from pathlib import Path
from django.shortcuts import render
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

BASE_DIR = Path(__file__).resolve().parent

# Create your views here.
cred = credentials.Certificate(BASE_DIR / "studentwellness-45958-firebase-adminsdk-pg4q7-7ec03943e8.json")
app = firebase_admin.initialize_app(cred)
db = firestore.client()

def index(request):
    # accessing our firestore data and storing it in a variable
    users_ref = db.collection(u'Users').document(u'testing4@gmail.com').collection(u'UserInfo')
    docs = users_ref.stream()
    
    for doc in docs:
        context = doc.to_dict()
        break
    
    # gender not accounted for at the moment
    x1 = 10.0 * 0.453592 * context['weight']
    x2 = 6.25 * 2.54 * (12.0 * context['height']['ft'] + context['height']['in'])
    x3 = 5.0 * (2023 - int(context['dob'][-4:]))
    context['BMR'] = x1 + x2 - x3

    return render(request, 'index.html', context)
