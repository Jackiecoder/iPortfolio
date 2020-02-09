from django.shortcuts import render
import requests
import sys
from subprocess import PIPE, run


def button(request):

    return render(request, "home.html")


def output(request):
    # data = requests.get("http://reqres.in/api/users")
    data = requests.get("http://www.google.com")
    print(data.text)
    data = data.text
    return render(request, "home.html", {'data': data})


def external(request):
    model = request.POST.get("model")
    company_name = request.POST.get("company_name")
    start = request.POST.get("start")
    end = request.POST.get("end")

    output_val = run([sys.executable,
                      "/Users/jackie/Documents/hackcwru/test.py", model, company_name, start, end], shell=False, stdout=PIPE)
    data_show = output_val.stdout.decode("utf-8")
    # print("the string is : ", data_show)
    return render(request, "home.html", {'data1': data_show})
