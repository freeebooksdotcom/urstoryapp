#based on https://github.com/jakerieger/FlaskIntroduction/
#additional coding https://sarahleejane.github.io/learning/python/2015/08/09/simple-tables-in-webapps-using-flask-and-pandas-with-python.html


from flask import Flask, render_template, redirect, url_for, request
import pandas as pd
import numpy as np
from scipy import spatial
import random
from spacy.lang.en import English
import pickle


app= Flask(__name__)

nlp = English().from_disk("spacymodel")



df=pd.read_csv('final_stories_no_vectors.csv', index_col=0)

df['vectors']=pickle.load(open( "vector.p", "rb" ))


def similarity(vec1, vec2):
    return 1- spatial.distance.cosine(vec1, vec2)

def query(user_input):
    doc=nlp(user_input)
    input_vector=doc.vector

    unsorted_sim=[(i, similarity(input_vector, df.loc[i, 'vectors'])) for i in df.index if df.loc[i, 'word_count']>100]
    results=sorted(unsorted_sim, key=lambda x: x[1], reverse=True)
    return results

def single_word_query(user_input):
    try:
        top_result=[i for i in df.index if user_input.lower() in df.loc[i, 'story_title'].lower().split(' ')][0]
        return find_similar_stories(top_result)
    except IndexError:
        doc = nlp(user_input)
        input_vector=doc.vector
        unsorted_sim=[(i, similarity(input_vector, df.loc[i, 'vectors'])) for i in df.index if df.loc[i, 'word_count']>100]
        results=sorted(unsorted_sim, key=lambda x: x[1], reverse=True)
        return results

def sample_results(results, n=12):
    strong_options=results[:n]
    medium_options=results[n:2*n]
    weak_options=results[2*n:3*n]

    sampled_items=[]
    for index in range(n//3):
        new_group= [strong_options[random.randint(0,n-1)], weak_options[random.randint(0,n-1)], medium_options[random.randint(0,n-1)]]
        sampled_items+=new_group
    return sampled_items

def make_story_dict(story_id, similarity=None):
    new_story_dict={}
    new_story_dict['story_title']=df.loc[story_id,'story_title']
    new_story_dict['book_title']=df.loc[story_id, 'book_title']
    new_story_dict['book_author']=df.loc[story_id,'book_author']
    new_story_dict['similarity']= similarity
    est_time=df.loc[story_id, 'word_count']//250 +1
    if est_time>1:
        new_story_dict['time_length']="About "+str(est_time)+" minutes"
    else:
        new_story_dict['time_length']="About "+str(est_time)+" minute"
    new_story_dict['story_id']=story_id

    for key, value in new_story_dict.items():
        if value=='frozenset()':
            new_story_dict[key]='Unknown'
    return new_story_dict

def find_similar_stories(story_id):
    story_vector=df.loc[story_id, 'vectors']
    unsorted_sim=[(i, similarity(story_vector, df.loc[i, 'vectors'])) for i in df.index if df.loc[i, 'word_count']>100]
    results=sorted(unsorted_sim, key=lambda x: x[1], reverse=True)
    return results[1:]

def make_gutenberg_link(story_id):
    gutenbergid= df.loc[story_id, 'book_id']
    gutenberglink='http://gutenberg.org/ebooks/'+str(gutenbergid)
    return gutenberglink

def slice_text(story_text):
    period_counter=0
    slices=[]
    abbrev=['Mr','rs','Dr']
    n=0
    for i in range(len(story_text[n:])):

        if story_text[i]=='.' or story_text[i]=='!':
            if story_text[i-2:i] in abbrev:
                continue
            else:
                period_counter+=1
                if period_counter==5:
                    slices.append(story_text[n:i+2])
                    n=i+1
                    period_counter=0

        elif i==len(story_text)-2:
            new=story_text[n:-1]
            if new not in slices[-2:]:
                slices.append(new)
            break

    return slices

@app.route("/", methods=['POST', 'GET'])
def index():
    organized_results=[]
    
    if request.method=='POST':
        user_query = request.form['content']

        if len(user_query.split(' '))>1:
            output = query(user_query)
        else:
            output = single_word_query(user_query)

        sampled=sample_results(output)

        for story_id, similarity in sampled:
            new_story_dict=make_story_dict(story_id, similarity)
            organized_results.append(new_story_dict)
        results = organized_results
        return render_template('index.html', results=results, user_query=user_query)
    else:
        results = organized_results
        return render_template('index.html', results=results)


@app.route('/read/<int:id>', methods=['GET', 'POST'])
def read(id):
    displayed_story= make_story_dict(id)
    story_text=slice_text(df.loc[id,'story_text'])
    gutenberglink=make_gutenberg_link(id)

    organized_results=[]
    if request.method=='POST':
        user_query = request.form['content']
        output = query(user_query)
        sampled=sample_results(output)

        for story_id, similarity in sampled:
            new_story_dict=make_story_dict(story_id, similarity)
            organized_results.append(new_story_dict)
        results = organized_results
        return redirect('index.html', results=results, user_query=user_query)

    else:
        output= find_similar_stories(id)
        sampled=sample_results(output)
        for story_id, similarity in sampled:
            new_story_dict=make_story_dict(story_id, similarity)
            organized_results.append(new_story_dict)
        results = organized_results
        return render_template('read.html', story=displayed_story, story_text= story_text, gutenberg= gutenberglink, results=results)


if __name__=="__main__":
    app.run(debug=True)
