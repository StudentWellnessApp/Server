import pandas as pd
import numpy as np

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from pathlib import Path

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import JSONParser

BASE_DIR = Path(__file__).resolve().parent

# Create your views here.
cred = credentials.Certificate(BASE_DIR / "studentwellness-45958-firebase-adminsdk-pg4q7-7ec03943e8.json")
app = firebase_admin.initialize_app(cred)
db = firestore.client()
        
@csrf_exempt
def getRecs(request):
    if request.method == 'POST':
        try:
            # load request information
            request_data = JSONParser().parse(request)

            # load exercises database
            df = pd.read_csv(BASE_DIR / 'exercises_final.csv')
            
            # accessing our firestore data and storing it in a variable
            user_info = db.collection(u'Users').document(request_data['user']).collection(u'UserInfo').document(request_data['user'])
            health_info = db.collection(u'Users').document(request_data['user']).collection(u'HealthInfo').document(request_data['date'])
            context = user_info.get().to_dict()
            context.update(health_info.get().to_dict())
            
            # calculate BMR (currently doesn't account for gender)
            x1 = 10.0 * 0.453592 * context['weight']
            x2 = 6.25 * 2.54 * (12.0 * context['height']['ft'] + context['height']['in'])
            x3 = 5.0 * (2023 - int(context['dob'][-4:]))
            context['BMR'] = x1 + x2 - x3

            # prepare filter artifacts & dataframe
            if context['exercisePref']['intensity'] == 'Light':
                context['Suggested Burn'] = context['BMR'] * 0.2
            elif context['exercisePref']['intensity'] == 'Moderate':
                context['Suggested Burn'] = context['BMR'] * 0.375
            elif context['exercisePref']['intensity'] == 'Intense':
                context['Suggested Burn'] = context['BMR'] * 0.55
            
            context['Suggested Burn'] = context['Suggested Burn'] - (context['walkCount'] * 0.04)
            df['Calories Burned'] = df['Calories Burned'] * context['weight']

            # filter based on gym access & hobbies
            if context['exercisePref']['gymAccess'] == 0:
                df = df[df['Equipment Required'] == 0]
            
            df = df[(df['Type'] == 'Strength Training') | (df['Type'] == 'Calisthenics') | (df['Type'] == 'Strength Training') | (df['Type'] == context['exercisePref']['hobbies'])]
            
            # filter based on type of last exercise
            last_ex = db.collection(u'Users').document(request_data['user']).collection(u'HealthInfo').document(u'LastExercise').get().to_dict()
            df = df[(df['Type'] != last_ex['Type'])]

            # rank based on caloric "distance" from suggested burn
            caloric_distance = abs(df['Calories Burned'] - context['Suggested Burn']).rename('Caloric Distance')
            caloric_distance = caloric_distance + (0.7 * np.random.rand(caloric_distance.shape[0])) # noise generation

            df = pd.concat([df, caloric_distance], axis=1)
            df = df.sort_values(by=['Caloric Distance']).reset_index(drop=True)

            # send results to firestore
            rec_1 = df.iloc[0].to_dict()
            rec_2 = df.iloc[1].to_dict()
            rec_3 = df.iloc[2].to_dict()
            
            db.collection(u'Users').document(request_data['user']).collection(u'HealthInfo').document(request_data['date']).collection(u'Exercises').document(u'Rec #1').set(rec_1)
            db.collection(u'Users').document(request_data['user']).collection(u'HealthInfo').document(request_data['date']).collection(u'Exercises').document(u'Rec #2').set(rec_2)
            db.collection(u'Users').document(request_data['user']).collection(u'HealthInfo').document(request_data['date']).collection(u'Exercises').document(u'Rec #3').set(rec_3)

            return JsonResponse("Recommendations Processed.", safe=False)
        except Exception as e:
            print(e.args[0])
            return JsonResponse("Request Failed.", safe=False)
