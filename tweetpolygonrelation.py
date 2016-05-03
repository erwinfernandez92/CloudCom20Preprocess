import couchdb
from couchdb.mapping import Document, TextField
import json
from shapely.geometry import Point
from shapely.geometry.geo import shape
import nltk
import csv
import pickle

dbhost = 'http://127.0.0.1:5984'
dbname_tweet = 'raw_tweets'
dbname_polygon = 'polygons'
dbname_relation = 'tweets_polygons_relational'
couch = couchdb.Server(dbhost)
dbtweet = couch[dbname_tweet]
dbpolygon = couch[dbname_polygon]

tweets =[]
NEG = "1"
POS = "2"
OT = "4"
rating =[NEG,POS,OT]

try:
    dbrelation = couch.create(dbname_relation)
except Exception as e:
    print('Error creating database (probably because it already exists)')
    print(str(e))
    dbrelation = couch[dbname_relation]

###############################################################################

class Tweet(Document):
    id = TextField()
    text = TextField()
    geo = TextField()

class Polygon(Document):
    geometry = TextField()
    properties = TextField()

###############################################################################

def get_words_in_tweets(tweets):
    all_words = []
    for (words, sentiment) in tweets:
        all_words.extend(words)
    return all_words

def get_word_features(wordlist):
    wordlist = nltk.FreqDist(wordlist)
    word_features = wordlist.keys()
    return word_features

def extract_features(document):
    document_words = set(document)
    features = {}
    for word in word_features:
        features['contains(%s)' % word] = (word in document_words)
    return features

def sentimentDecider(tweet):
    if ((classifier.classify(extract_features(tweet.split())))=="1"):
        return "negative"
    else if ((classifier.classify(extract_features(tweet.split())))=="2"):
        return "positive"
    else if ((classifier.classify(extract_features(tweet.split())))=="2"):
        return "neutral"

###############################################################################
#this section is preparing classifier for determining the tweet's sentiment
#Reading the training set for sentiment analysis that has been obtained from internet
with open ("trainSet.tsv") as tsvfile:
    tsvreader = csv.reader(tsvfile, delimiter="\t")
    for line in tsvreader:
        try:
            words_filtered=[e.lower() for e in line[2].split() if len(e) >= 3]
            if (line[5] in rating):
                tweets.append((words_filtered,line[5]))
            if (line[6] in rating):
                tweets.append((words_filtered,line[6]))
            if (line[7] in rating):
                tweets.append((words_filtered,line[7]))
            if (line[8] in rating):
                tweets.append((words_filtered,line[8]))
            if (line[9] in rating):
                tweets.append((words_filtered,line[9]))
            if (line[10] in rating):
                tweets.append((words_filtered,line[10]))
            if (line[11] in rating):
                tweets.append((words_filtered,line[11]))
            if (line[12] in rating):
                tweets.append((words_filtered,line[12]))
        except IndexError:
            continue

word_features = get_word_features(get_words_in_tweets(tweets))
training_set = nltk.classify.apply_features(extract_features, tweets)
#to save running time, the classifier has been made beforehand and 
#saved into a pickle file using the code below
#
# classifier = nltk.NaiveBayesClassifier.train(training_set)
# f = open('my_classifier.pickle', 'wb')
# pickle.dump(classifier,f)
# f.close()

#retrieving classifier that has been created
f = open('my_classifier.pickle', 'rb')
classifier = pickle.load(f)
f.close()

###############################################################################

for tweet_id in dbtweet:
    # load the Tweet from the database into a Tweet object
    tweet = Tweet.load(dbtweet, tweet_id)
    if tweet.geo != None:
        tweet_geo = tweet.geo.replace("'", '"')
        tweet_geo = json.loads(tweet_geo)
        # create a Point object from the coordinates
        tweet_point = Point(tweet_geo['coordinates'][1], tweet_geo['coordinates'][0])
        print("Tweet ID:", tweet_id)
        print("Tweet location:", tweet_point)
        # load the Polygon database
        for polygon_id in dbpolygon:
            polygon_ob = Polygon.load(dbpolygon, polygon_id)
            if polygon_ob.geometry != None:
                temp1 = polygon_ob.geometry.replace("'", '"')
                temp2 = json.loads(temp1)
                polygon = shape(temp2)
                # look if this polygon contains the tweet_point
                if(polygon.contains(tweet_point)):
                    print("Found a polygon:", polygon_id)
                    sentiment = sentimentDecider(tweet.text)
                    doc = {"tweet_id" : tweet_id, "polygon_id" : polygon_id, "sentiment" : sentiment}
                    dbrelation.save(doc)
                    break
        # for feature in js['features']:
        #     if(feature['geometry'] != None):
        #         polygon = shape(feature['geometry'])
        #         if(polygon.contains(tweet_point)):
        #             print("Found containing polygon:", feature)
        # for polygon_id in dbrelation:
        #     print(polygon_id)
        #     polygon = Polygon.load(dbrelation, polygon_id)
        #     polygon_features = polygon.features.replace("'", '"')
        #     polygon_json = json.loads(polygon_features)
        #     for feature in polygon_json:
        #         polygon = shape(feature['geometry'])
        #         if(polygon.contains(tweet_point)):
        #             print("Found containing polygon:", feature)
