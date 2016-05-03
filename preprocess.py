from couchdb import design, Server
import json
from shapely.geometry import Point
from shapely.geometry.geo import shape
import nltk
import csv
import pickle

dbhost = 'http://127.0.0.1:5984'
dbname_tweet = 'raw_tweets'
dbname_relation = 'tweets_polygons_relational'
couch = Server(dbhost)
dbtweet = couch[dbname_tweet]

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
    elif ((classifier.classify(extract_features(tweet.split())))=="2"):
        return "positive"
    elif ((classifier.classify(extract_features(tweet.split())))=="4"):
        return "neutral"

###############################################################################
# This section is preparing classifier for determining the tweet's sentiment
# Reading the training set for sentiment analysis that has been obtained from
# internet.
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
# to save running time, the classifier has been made beforehand and
# saved into a pickle file using the code below
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

# this function takes a polygon json file and returns a dictionary with
# a key of the polygon ID and a value of the polygon shape
def storePolygons(jsonfile):
    with open(jsonfile) as data_file:
        js = json.load(data_file)

    list_of_polygons = {}

    for feature in js['features']:
        if feature['geometry']:
            polygon_id = feature['properties']['SA2_MAIN11']
            list_of_polygons[polygon_id] = shape(feature['geometry'])
    return list_of_polygons

# this fucntion takes a raw tweet database and use a map reduce function to
# filter the tweet with no geo value
def tweetReduce(dbtweet):
    mapFunc = '''function(doc) {
        if(doc.coordinates && !doc.preprocessed) {
            emit(doc._id, null);
            }
        }'''
    view = design.ViewDefinition('tweets', 'reduced', mapFunc)
    view.sync(dbtweet)

# this function preprocesses the tweets to get the location of the tweets
# identified by the polygon and the sentiment of the tweets, and then stores
# them in a database
def preprocess(dbtweet, list_of_polygons, dbrelation):
    viewResults = dbtweet.view('tweets/reduced')
    for result in viewResults:
        tweet_id = result.id
        tweet = dbtweet[tweet_id]
        tweet_geo = tweet['coordinates']
        # create a Point object from the coordinates
        tweet_point = Point(tweet_geo['coordinates'][0],
                            tweet_geo['coordinates'][1])
        print("Tweet ID:", tweet_id)
        print("Tweet location:", tweet_point)
        for polygon_id in list_of_polygons:
            if(list_of_polygons[polygon_id].contains(tweet_point)):
                print("Found a polygon:", polygon_id)
                sentiment = sentimentDecider(tweet['text'])
                print("Tweet:", tweet['text'])
                print("Sentiment:",sentiment)
                doc = {"tweet_id" : tweet_id, "polygon_id" : polygon_id,
                    "sentiment" : sentiment}
                dbrelation.save(doc)
                break
        # having done the preprocessing, it adds a new attribute called
        # 'preprocessed' and set it as True and then update the raw tweet
        # database
        tweet['preprocessed'] = True
        dbtweet[tweet_id] = tweet

jsonfile = 'geojsonfile_mapshaper_simplified.json'
list_of_polygons = storePolygons(jsonfile)
tweetReduce(dbtweet)
preprocess(dbtweet, list_of_polygons, dbrelation)
