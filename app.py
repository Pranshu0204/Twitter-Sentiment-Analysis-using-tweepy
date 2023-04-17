import tweepy
import numpy as np
from textblobing import TextBlob
from flask import Flask, render_template, request,redirect,session,jsonify
from cleantext import clean_tweet

app=Flask(__name__,static_folder="static")

consumer_key = 'your consumer key'
consumer_secret='your consumer secret'

access_token='your access token'
access_token_secret='your access token secret'

auth=tweepy.OAuthHandler(consumer_key,consumer_secret)
auth.set_access_token(access_token,access_token_secret)

api=tweepy.API(auth)

# def home():
#     return render_template('index.html')
@app.route("/analysis",methods=['POST'])
def tweet_analysis():
    if request.method== "POST":
        ques=request.form['ques']
    query=ques + "-filter:retweets"
    tweets=api.search_tweets(q=query,lang='en',count=5,result_type='popular')

    subjectivities= []
    polarities=[]
    vals=[]

    print_result="none"
    for tweet in tweets:
        tweet.text=clean(tweet.text, no_emoji=True)
        phrase=TextBlob(tweet.text)
        if phrase.sentiment.polarity != 0.0 and phraase.sentiment.subjectivity !=0.0:
            polarities.append(phrase.sentiment.polarity)
            subjectivities.append(phrase.sentiment.subjectivity)
            vals.append(tweet.text)

        print('Tweet: '+tweet.text)
        print('Polarity: '+ str(phrase.sentiment.polarity) + '\Subjectivity: '+ str(phrase.sentiment.subjectivity))
        print('..........................')

    result= {'polarity':polarities,'subjectivity':subjectivities}

    get_weighted_polarity_mean= np.average(resukt['polarity'], weights=result['subjectivity'])

    get_polarity_mean=np.mean(result['polarity'])


    if get_polarity_mean >0.0:
        print_result="POSITIVE"
    elif get_polarity_mean ==0.0:
        print_result="NEUTRAL"
    else:
        print_result="NEGATIVE"

    
    RES= {'polarity':polarities,
          'subjectivity':subjectivities,
          'values':vals,
          'get_weighted_polarity_mean':get_weighted_polarity_mean,
          'get_polarity_mean':get_polarity_mean,
          'RESULT': print_result
          }
    
    return jsonify(RES)

if __name__ == "__main__":
    app.run(debug=True)


