import os
import sys
import json
import subprocess
from collections import defaultdict

from django.conf import settings
from django.shortcuts import render
from django.http import FileResponse, StreamingHttpResponse
from rest_framework.decorators import api_view, parser_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from ChatBot_functions.chat_helpers import *

def get_folder(ext):
    if ext.lower()=='.pdf': return 'pdfs'
    elif ext.lower() in ['.doc','.docx']: return 'docs'
    elif ext.lower() in ['.png', '.jpg', '.jpeg']: return 'images'
    elif ext.lower()=='.txt': return 'txts'
    else: return 'error'

@api_view(["POST"])
def get_response(request):
    user_message = request.data.get('question', '')
    if not user_message:
        return Response({'error': 'No Question Provided'}, status=400)

    if not os.path.exists(CURRENT_VECTORDB_PATH):
        return Response({'error': 'No documents uploaded yet. Please upload documents first.'}, status=400)

    try:
        reply = get_reply(user_message)
    except Exception as e:
        return Response({'error': f'Failed to get response: {str(e)}'}, status=500)

    return Response({
        'question': user_message,
        'response': reply
    }, status=200)

@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def upload_file(request):
    uploaded_file_lst = request.FILES.getlist('file')
    rename_data = request.POST.get('rename')
    if rename_data: rename_data = json.loads(rename_data)
    saved_files, error_files = [],[]
    # custom_name = request.data.get('filename','').strip()
    
    if not uploaded_file_lst: return Response({'error': 'No File Provided'}, status=400)
    clear_staging()
    
    for uploaded_file in uploaded_file_lst:
        original_name, ext = os.path.splitext(uploaded_file.name)
        file_name = rename_data.get(original_name) if original_name in rename_data else original_name
        
        save_dir = os.path.join(settings.MEDIA_ROOT, 'staging', get_folder(ext))
        final_dir = os.path.join(settings.MEDIA_ROOT, get_folder(ext))
        
        if ext not in ['.doc','.docx','.pdf','.png', '.jpg', '.jpeg','.txt']:
            error_files.append(f"{original_name+ext}: Status code:415 Unsupported file tye only Pdf, Word, Text And Image files are allowed.")
            continue
        
        file_path = os.path.join(save_dir, file_name+ext)
        final_file_path = os.path.join(final_dir, file_name+ext)
        
        if os.path.exists(file_path):
            error_files.append(f"{original_name+ext}: Status code:409 File Already Exists in the current upload ignoring the current file.")
            continue
        
        if os.path.exists(final_file_path):
            error_files.append(f"{original_name+ext}: Status code:409 File Already Exists either rename the file or delete the Existing file:{file_name+ext}.")
            continue
        
        with open(file_path,'wb') as file:
            for chunk in uploaded_file.chunks():
                file.write(chunk)
        saved_files.append(file_name+ext)
    
    if saved_files!=[]:
        docs,process_all_files = load_documents(False)
        add_documents_vectordb(docs, process_all_files)
            
    
    print('Moving the files from staging to actual folders')
    move_folder_contents(STAGING_FOLDER, BASE_DATA_DIR)
    
    return Response({
        'message': f'Successfully uploaded {len(saved_files)} files. Error prone {len(error_files)} files. Created New VectorDB and Chat_History from existing with the mentioned saved files' ,
        'saved_files': saved_files,
        'error_files': error_files
    }, status = 201)

@api_view(['GET'])
def get_file(request):
    headers = request.headers
    filename = request.GET.get('filename')
    if not filename: return Response({'error': "Missing 'filename' parameter"}, status=400)
    
    _, ext = os.path.splitext(filename)
    filepath = os.path.join(settings.MEDIA_ROOT, get_folder(ext), filename)
    
    if not os.path.exists(filepath): return Response({'error': "File doesn't exist"}, status=404)
    
    return FileResponse(open(filepath,'rb'), as_attachment=True, content_type=headers.get('X-Custom-Response-Format','application/octet-stream'))   

@api_view(['GET'])
def list_files(request):
    data = defaultdict(list)
    
    for root, dirs, files in os.walk(settings.MEDIA_ROOT):
        for file in files:
            if root.split('/')[-1]=='txts': data['text_files'].append(file)
            elif root.split('/')[-1]=='pdfs': data['pdf_files'].append(file)
            elif root.split('/')[-1]=='docs': data['word_files'].append(file)
            elif root.split('/')[-1]=='images': data['image_files'].append(file)
    
    return Response(data)

@api_view(['DELETE'])
def delete_file(request):
    filename = request.GET.get('filename')
    if not filename: return Response({'error': "Missing 'filename' parameter"}, status=400)
    _, ext = os.path.splitext(filename)
    filepath = os.path.join(settings.MEDIA_ROOT, get_folder(ext), filename)
    
    if not os.path.exists(filepath): return Response({'error': "File doesn't exist"}, status=404)
    
    try:
        filedata = open(filepath, 'rb')
        os.remove(filepath)
        recreate_vectordb()
        return FileResponse(filedata, as_attachment=True, content_type='application/octet-stream')
    except Exception as error:
        return Response({"error": f"Couldn't delte file due to {str(error)}"}, status=500)

@api_view(['GET'])
def list_models(request):
    os_model_lst = subprocess.check_output(['ollama','list']).decode('utf-8')
    os_model_lst = [[j for j in i.split('  ') if j.strip()!=''] for i in os_model_lst.split('\n') if [j for j in i.split('  ') if j.strip()!='']!=[]]
    ollama_model_names = [i[0].split(':')[0].strip() for i in os_model_lst[1:]]
    data = {'present models':ollama_model_names}
    return Response(data)

@api_view(['GET'])
def current_model(request):
    data = {'current selected model':MODEL}
    return Response(data)

@api_view(['POST'])
def add_model(request):
    model_name = request.GET.get('model_name')
    os_model_lst = subprocess.check_output(['ollama','list']).decode('utf-8')
    os_model_lst = [[j for j in i.split('  ') if j.strip()!=''] for i in os_model_lst.split('\n') if [j for j in i.split('  ') if j.strip()!='']!=[]]
    ollama_model_names = [i[0].split(':')[0].strip() for i in os_model_lst[1:]]
    if model_name in ollama_model_names:
        os.system(f'ollama pull {model_name}')
    else: return Response({'error': "Model doesn't exist"}, status=404)
    ollama_model_names.remove(model_name)
    data = {'present models':ollama_model_names}
    return Response(data)

@api_view(['POST'])
def select_model(request):
    model_name = request.GET.get('model_name')
    if not model_name:
        return Response({'error': 'Missing model_name parameter'}, status=400)

    constants_path = os.path.join(settings.BASE_DIR, 'ChatBot_functions', 'constants.py')
    try:
        with open(constants_path, 'r') as file:
            lines = file.readlines()
        for i, line in enumerate(lines):
            if line.strip().startswith('MODEL'):
                lines[i] = f"MODEL = '{model_name}'\n"
        with open(constants_path, 'w') as file:
            file.writelines(lines)
    except Exception as e:
        return Response({'error': f'Failed to update model: {str(e)}'}, status=500)

    data = {'selected_model': model_name}
    return Response(data)

@api_view(['DELETE'])
def delete_model(request):
    model_name = request.GET.get('model_name')
    os.system(f'ollama rm {model_name}')
    os_model_lst = subprocess.check_output(['ollama','list']).decode('utf-8')
    os_model_lst = [[j for j in i.split('  ') if j.strip()!=''] for i in os_model_lst.split('\n') if [j for j in i.split('  ') if j.strip()!='']!=[]]
    ollama_model_names = [i[0].split(':')[0].strip() for i in os_model_lst[1:]]
    data = {'present models':ollama_model_names}
    return Response(data)


def ui(request):
    return render(request, 'myapi/index.html')