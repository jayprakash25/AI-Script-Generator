from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
import json, os
from pytube import YouTube
import assemblyai as aai
import openai
from .models import BlogPost

aai.settings.api_key = "10b019defc5042bdb66c853656c48cc9"
# Create your views here.
@login_required
def index(request):
    return render(request, 'index.html')

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password = password)

        if user is not None:
            login(request, user)
            return redirect('/')
        else:
            return render(request, 'login.html')    

    return render(request, 'login.html')



def user_signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']

        try:
            user = User.objects.create_user(username,email, password)
            user.save()
            login(request, user)
            return redirect('/')
        except:
            return render(request, 'signup.html');

    return render(request, 'signup.html')

def user_logout(request):
    logout(request)
    return redirect('/')

@csrf_exempt
def generate_blog(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            yt_Link = data['link']
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({'error': 'Invalid data sent'}, status=400)
            
        
        # get yt title 

        title = yt_title(yt_Link)
        
        # get transcript 

        transcription = get_transcription(yt_Link)
        if not transcription:
            return JsonResponse({'error': "Failed to get script"}, status=500)

        # use OpenAI 
        blog_content = gen_script_from_transcription(transcription)
        if not blog_content:
                return JsonResponse({'error': "Failed to get script"}, status=500)



        # save to db
        new_blog_script = BlogPost.objects.create(
            user = request.user,
            youtube_title = title,
            youtube_link = yt_Link,
            generated_content = blog_content
        )

        new_blog_script.save()

        # return blog as respone 
        return JsonResponse({'content': blog_content})
    else:
        return JsonResponse({'error' : 'Invalid request'}, status = 405 )
    
    
def yt_title(link):
    yt = YouTube(link)
    title = yt.title
    return title

def dowd_audio(link):
    yt = YouTube(link)
    video = yt.streams.filter(only_audio = True).first()
    out_file = video.download(output_path=settings.MEDIA_ROOT)
    base, ext = os.path.splitext(out_file)
    new_file = base + '.mp3'
    if os.path.exists(new_file):
        os.remove(new_file)
    os.rename(out_file, new_file)
    return new_file

def get_transcription(link):
    audio_file = dowd_audio(link)
    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_file)

    return transcript.text

def gen_script_from_transcription(transcription):
    openai.api_key = "sk-proj-lBK1IRHedQIe5GrkGgabT3BlbkFJatqn1WoiAUVIFznGBsLy"

    prompt = f"Create a blog post based on the provided YouTube video . The content should be transformed to fit a written format with a clear narrative, engaging headings, and detailed explanations. Ensure it doesn't resemble a video script and is tailored for a reading audience, complete with an introduction and conclusion. The YouTube video content: \n\n{transcription}\n\n"
    response = openai.completions.create(
        model='gpt-3.5-turbo-instruct',
        prompt = prompt,
        max_tokens = 1000
    )

    generated_content = response.choices[0].text.strip()

    return generated_content


def blog_list(request):
    blog = BlogPost.objects.filter(user = request.user)
    return render(request, 'all-blogs.html', {'blogs' : blog})

def blog_details(request, pk):
    blog_detail = BlogPost.objects.get(id=pk)
    if request.user == blog_detail.user:
        return render(request, 'blog-details.html', {{'blog-detail': blog_detail}})
    else:
        return redirect('/')


