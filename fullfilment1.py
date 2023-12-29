from flask import Flask, request, jsonify
import fitz
import spacy
from flask_cors import CORS
import requests
import time
#
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
#
import pandas as pd
import re

def resume_fetch():
    #fname = 'Data-Analyst-Resume-2.pdf'
    fname = 'sample_input.pdf'
    doc = fitz.open(fname)
    text = ""
    for page in doc:
        text = text + str(page.get_text())

    tx = " ".join(text.split('\n'))
    # count no.of pages in pdf
    num_pages = doc.page_count
    doc.close()
    return tx, num_pages

def job_postings_search(desig,loc):
    # Set the path to the chromedriver executable
    #chromedriver_path = 'C:\\Windows\\chromedriver.exe'
    # Create a new instance of the Chrome driver
    driver = webdriver.Chrome()
    # Navigate to the Indeed website
    driver.get('https://in.indeed.com/')
    time.sleep(3)
    # Find the search input elements and location input element
    search_input = driver.find_element(By.ID, 'text-input-what')

    location_input = driver.find_element(By.ID, 'text-input-where')

    # Enter the search query and location
    search_input.send_keys(desig)
    location_input.send_keys(loc)
    time.sleep(3)
    # Submit the search form
    search_form = driver.find_element(By.CLASS_NAME, 'yosegi-InlineWhatWhere-primaryButton')
    search_form.submit()
    time.sleep(3)
    # sort by date
    date_sort = driver.find_element(By.PARTIAL_LINK_TEXT, 'date')
    date_sort.click()

    # let the driver wait 3 seconds to locate the element before exiting out
    driver.implicitly_wait(3)
    titles = []
    companies = []
    locations = []
    links = []
    reviews = []
    salaries = []
    descriptions = []

    for i in range(0, 1):

        job_card = driver.find_elements(By.CLASS_NAME, 'job_seen_beacon')

        for job in job_card:

            # .  not all companies have review
            try:
                review = job.find_element(By.XPATH, './/span[@class="css-1h3qsl9 eu4oa1w0"]').text
            except:
                review = "None"
            reviews.append(review)
            # .   not all positions have salary
            try:
                salary = job.find_element(By.XPATH, './/div[contains(@class,"css-1ihavw2 eu4oa1w0")]').text
            except:
                salary = "None"
            # .  tells only to look at the element
            salaries.append(salary)

            try:
                location = job.find_element(By.XPATH, './/div[contains(@class,"css-t4u72d eu4oa1w0")]').text
            except:
                location = "None"
            # .  tells only to look at the element
            locations.append(location)

            try:
                title = job.find_element(By.XPATH,'.//h2[@class="jobTitle jobTitle-newJob css-j45z4f eu4oa1w0"]//a').text
            except:
                title = job.find_element(By.XPATH, './/h2[@class="jobTitle jobTitle-newJob css-mr1oe7 eu4oa1w0"]//a').get_attribute(name="title")
            titles.append(title)
            try:
                link = job.find_element(By.XPATH,'.//h2[@class="jobTitle jobTitle-newJob css-j45z4f eu4oa1w0"]//a').get_attribute(name="href")
            except:
                link = job.find_element(By.XPATH,'.//h2[@class="jobTitle jobTitle-newJob css-mr1oe7 eu4oa1w0"]//a').get_attribute(name="href")
            links.append(link)
            companies.append(job.find_element(By.XPATH, './/span[@class="css-1x7z1ps eu4oa1w0"]').text)

    for link in links:
        driver.get(link)
        jd = driver.find_element(By.XPATH, '//div[@id="jobDescriptionText"]').text
        descriptions.append(jd)
    df = pd.DataFrame()
    df['Title'] = titles
    df['Company'] = companies
    df['Location'] = locations
    df['Link'] = links
    df['Rating'] = reviews
    df['Salary'] = salaries
    df['Description'] = descriptions

    df['Description'] = df["Description"].str.replace('\n', ' ')
    df['Description'] = df['Description'].apply(lambda x: re.sub(r'\s+', ' ', x).strip())  # Strip leading/trailing spaces

    # Close the browser
    driver.quit()

    return df[0:3], df[3:6]

app = Flask(__name__)
unmatched_job_skills1 =[]  # Global variable for job skills
unmatched_job_skills2 =[]

#@app.route('/', methods=['POST'])
def test():
    data = request.get_json()
    intent_name = data['queryResult']['intent']['displayName']
    print(intent_name)
    response = {'fulfillmentText': "Hello"}
    if intent_name == 'ResumeUpload Intent':
       return resume_upload_response()
        #return jsonify(response)
    elif intent_name == 'Confirmation Intent':
      # return confirm_and_job_match()[0]
       return jsonify(response)
    elif intent_name == 'Next Job Intent':
        #return next_job_match()[0]
        return jsonify(response)
    elif intent_name == 'Resume Improvement Intent':
        #return course_suggest()
        return jsonify(response)
    else:
        response = {
            'fulfillmentText': 'Invalid intent'
        }
        return jsonify(response)

#return requests.post(headers={"Content-Type": "application/json"},data=resume_upload_response())

"""
@app.route('/', methods=['POST'])
def index():
    data = request.get_json()
    print(data)
    intent_name = data['queryResult']['intent']['displayName']
    print(intent_name)
    if intent_name == 'ResumeUpload Intent':
        response = {'fulfillmentText': "Hello"}

    return jsonify(response)
"""


@app.route('/')
def resume_upload_response():
    model_dir = "./custom_model1"
    nlp = spacy.load(model_dir)
    doc = nlp(resume_fetch()[0])
    i = 0
    j = 0
    dct = {}
    email = []
    for ent in doc.ents:
        # Print the entity text and its label
        # print(ent.text, ent.label_)
        if ent.label_ == "PERSON" and i == 0:
            dct['Name'] = ent.text
            i = i + 1
        #if ent.label_ == "EMAIL":
            #email.append(ent.text)
        if ent.label_ == "GPE" and j == 0:
            dct['Location'] = ent.text
            j = j + 1
    num_pages = resume_fetch()[1]

    # custom trained model for designation, years of experience, degree
    custom_nlp = spacy.load('./model_train1/output/model-best')
    doc1 = custom_nlp(resume_fetch()[0])

    r = {}
    i = 0
    for ent in doc1.ents:
        if ent.label_ == "Designation" and i == 0:
            r['Job_title'] = ent.text
            print(r['Job_title'])
            i = i + 1
    if num_pages == 1:
        job_title = "Junior" + " " + r['Job_title']
    else:
        job_title = "Senior" + " " + r['Job_title']
    #print("Number of pages in the resume:", num_pages)

    response = {
        'fulfillmentText':"Hi {}! Thank you for providing your resume. Based on my analysis, it appears you are interested in applying for the position of {} in {}. Is that correct?".format(dct['Name'],job_title,dct['Location'])
    }
    print(response)
    return jsonify(response)

@app.route('/a')
def confirm_and_job_match():
    # custom trained model for designation, years of experience (YoE), degree
    custom_nlp1 = spacy.load('./model_train1/output/model-best')
    ######################
    # for resume
    #####################
    doc_resume1 = custom_nlp1(resume_fetch()[0])
    i = 0
    r = {}
    degrees_resume = []
    years_of_exp_resume = []
    for ent in doc_resume1.ents:
        if ent.label_ == "Designation" and i == 0:
            r['Job_title'] = ent.text
            i = i+1
        if ent.label_ == "Degree":
            degrees_resume.append(ent.text)
        if ent.label_ == "Years":
            years_of_exp_resume.append(ent.text)

    # detect no.of pages
    resume_pages = resume_fetch()[1]
    if resume_pages == 1:
        r['Job_title'] = "Junior" + " " + r['Job_title']
    else:
        r['Job_title'] = "Senior" + " " + r['Job_title']

    print(r['Job_title'])

    # custom model for job skills and candidate location
    model_dir = "./custom_model1"
    custom_nlp2 = spacy.load(model_dir)
    doc_resume = custom_nlp2(resume_fetch()[0])
    resume_skills = []
    j = 0
    dct = {}
    for ent in doc_resume.ents:
        if ent.label_ == "SKILL":
            resume_skills.append(ent.text)
        if ent.label_ == "GPE" and j == 0:
            dct["Location"] = ent.text
            j = j+1

    print(resume_skills)

    ######################
    # for job posts (Indeed website)
    # job posting details , skills, years of experience, degree, jobs title from resume
    #####################
    # live job postings data
    job_post_data = job_postings_search(r['Job_title'],dct["Location"])[0]

#######################################################################################
    # extract degree and YoE
    # for 3 job posts
#########################################################################################
    job_post_desc1 = []
    for desc in job_post_data['Description']:
        job_post_desc1.append(desc)

    job_deg_year = []
    for i in job_post_desc1:
        x = custom_nlp1(i)
        job_deg_year.append(x)

    degrees = []
    years_of_exp = []

    for jdy in job_deg_year:
        temp_degrees = []
        temp_years_of_exp = []

        for ent1 in jdy.ents:
            if ent1.label_ == "Degree":
                temp_degrees.append(ent1.text)
            if ent1.label_ == "Years":
                temp_years_of_exp.append(ent1.text)

        degrees.append(temp_degrees)
        years_of_exp.append(temp_years_of_exp)

#######################################################################################
    # extract SKILLS
    # for 3 job posts
#########################################################################################
    job_post_desc2 = []
    for i in job_post_data['Description']:
        job_post_desc = custom_nlp2(i)
        job_post_desc2.append(job_post_desc)

    job_skills = []
    for x in job_post_desc2:
        temp_skills = []
        for ent2 in x.ents:
            if ent2.label_ == "SKILL":
                temp_skills.append(ent2.text)
        job_skills.append(temp_skills)

########################ATS###################################################################################################
# generating score by using a custom ATS algorithm using semantic matching
# compares between "degrees_resume" vs "degrees" ,"years_of_exp_resume" vs "years_of_exp", "resume_skills" vs "job_skills"
# Generates a score out of 100 , the threshold should be 0.7
################################################################################################################################
    # Load the pre-trained word embeddings model
    nlp = spacy.load('en_core_web_md')

    # Calculate the semantic similarity between skills in the resume and job posting
    skills_similarity = []
    for skills_resume in resume_skills:
        temp_similarity = []
        for skills_job_list in job_skills:
            for skills_job in skills_job_list:
                similarity = nlp(skills_resume).similarity(nlp(skills_job))
                temp_similarity.append(similarity)
        skills_similarity.append(temp_similarity)

    # Calculate the semantic similarity score for each job posting
    semantic_scores = []
    for i in range(len(job_post_data)):
        degree_match = set()
        if degrees_resume and degrees[i]:  # checks if the list is empty
            for degree in degrees_resume:
                for degree_job in degrees[i]:
                    similarity = nlp(degree).similarity(nlp(degree_job))
                    if similarity >= 0.7:  # Set a threshold for similarity score
                        degree_match.add(degree)

    # calculate the YoE
        years_of_exp_match = set()
        if years_of_exp_resume and years_of_exp[i]:
            if years_of_exp_resume >= years_of_exp[i]:
                years_of_exp_match.add(years_of_exp_resume)

        # Calculate the average semantic similarity score for skills
        avg_skills_similarity = sum(skills_similarity[i]) / len(skills_similarity[i])

        # Calculate the overall score by combining matches and semantic similarity
        score = len(degree_match) + len(years_of_exp_match) + avg_skills_similarity
        score /= (len(degrees_resume) + len(years_of_exp_resume) + 1)  # Add 1 to account for the average similarity
        semantic_scores.append(score)

        #global umatched_job_skills
        global unmatched_job_skills1
        unmatched_job_skills1 =[]
        # Append unmatched job skills to the global list
        for skills_resume in resume_skills:
            for skills_job_list in job_skills:
                for skills_job in skills_job_list:
                    if nlp(skills_resume).similarity(nlp(skills_job)) <= 0.7:
                        unmatched_job_skills1.append(skills_job)

    response = {
    'fulfillmentText':"""Understood. I have found three recent job postings for the position of {}. Here are the details:

1. {}, {}, {}, {}, {}, {}
2. {}, {}, {}, {}, {}, {}
3. {}, {}, {}, {}, {}, {}

To be eligible, a match score of 0.7 or greater is required. However, based on your qualifications, your current score is below this threshold, and you are unable to apply for any of these positions. Would you like to explore the next set of job postings?""".format(r['Job_title'],job_post_data['Company'][0],job_post_data['Title'][0], job_post_data['Location'][0],job_post_data['Salary'][0],job_post_data['Rating'][0],semantic_scores[0],job_post_data['Company'][1],job_post_data['Title'][1], job_post_data['Location'][1],job_post_data['Salary'][1],job_post_data['Rating'][1],semantic_scores[1],job_post_data['Company'][2], job_post_data['Title'][2],job_post_data['Location'][2],job_post_data['Salary'][2],job_post_data['Rating'][2],semantic_scores[2] )
    }
    print(response)
    return jsonify(response), unmatched_job_skills1

@app.route('/b')
def next_job_match():
    #global unmatched_job_skills
    # custom trained model for designation, years of experience, degree
    custom_nlp1 = spacy.load('./model_train1/output/model-best')
    # for resume
    doc_resume1 = custom_nlp1(resume_fetch()[0])
    i = 0
    r = {}
    degrees_resume = []
    years_of_exp_resume = []
    for ent in doc_resume1.ents:
        if ent.label_ == "Designation" and i == 0:
            r['Job_title'] = ent.text
            i = i + 1
        if ent.label_ == "Degree":
            degrees_resume.append(ent.text)
        if ent.label_ == "Years":
            years_of_exp_resume.append(ent.text)

    resume_pages = resume_fetch()[1]
    if resume_pages == 1:
        r['Job_title'] = "Junior" + " " + r['Job_title']
    else:
        r['Job_title'] = "Senior" + " " + r['Job_title']

    model_dir = "./custom_model1"
    custom_nlp2 = spacy.load(model_dir)
    doc_resume = custom_nlp2(resume_fetch()[0])
    resume_skills = []
    j = 0
    dct = {}
    for ent in doc_resume.ents:
        if ent.label_ == "SKILL":
            resume_skills.append(ent.text)
        if ent.label_ == "GPE" and j == 0:
            dct["Location"] = ent.text
            j = j + 1

    print(resume_skills)

    ### job posting details , skills, years of experience, degree, jobs title from resume

    # live job postings data
    job_post_data = job_postings_search(r['Job_title'], dct["Location"])[1]

    # for 3 job posts
    job_post_desc1 = []
    for desc in job_post_data['Description']:
        job_post_desc1.append(desc)

    job_deg_year = []
    for i in job_post_desc1:
        x = custom_nlp1(i)
        job_deg_year.append(x)

    degrees = []
    years_of_exp = []

    for jdy in job_deg_year:
        temp_degrees = []
        temp_years_of_exp = []

        for ent1 in jdy.ents:
            if ent1.label_ == "Degree":
                temp_degrees.append(ent1.text)
            if ent1.label_ == "Years":
                temp_years_of_exp.append(ent1.text)

        degrees.append(temp_degrees)
        years_of_exp.append(temp_years_of_exp)

    job_post_desc2 = []
    for i in job_post_data['Description']:
        job_post_desc = custom_nlp2(i)
        job_post_desc2.append(job_post_desc)

    job_skills = []
    for x in job_post_desc2:
        temp_skills = []
        for ent2 in x.ents:
            if ent2.label_ == "SKILL":
                temp_skills.append(ent2.text)
        job_skills.append(temp_skills)

########################ATS###################################################################################################
# generating score by using a custom ATS algorithm using semantic matching
# compares between "degrees_resume" vs "degrees" ,"years_of_exp_resume" vs "years_of_exp", "resume_skills" vs "job_skills"
# Generates a score out of 100 , the threshold should be 0.7
################################################################################################################################
    # Load the pre-trained word embeddings model
    nlp = spacy.load('en_core_web_md')

    # Calculate the semantic similarity between skills in the resume and job posting
    skills_similarity = []
    for skills_resume in resume_skills:
        temp_similarity = []
        for skills_job_list in job_skills:
            for skills_job in skills_job_list:
                similarity = nlp(skills_resume).similarity(nlp(skills_job))
                temp_similarity.append(similarity)
        skills_similarity.append(temp_similarity)

    # Calculate the semantic similarity score for each job posting
    semantic_scores = []
    for i in range(len(job_post_data)):
        degree_match = set()
        if degrees_resume and degrees[i]:  # checks if the list is empty
            for degree in degrees_resume:
                for degree_job in degrees[i]:
                    similarity = nlp(degree).similarity(nlp(degree_job))
                    if similarity >= 0.7:  # Set a threshold for similarity score
                        degree_match.add(degree)

        years_of_exp_match = set()
        if years_of_exp_resume and years_of_exp[i]:
            if years_of_exp_resume >= years_of_exp[i]:
                years_of_exp_match.add(years_of_exp_resume)

        # Calculate the average semantic similarity score for skills
        avg_skills_similarity = sum(skills_similarity[i]) / len(skills_similarity[i])

        # Calculate the overall score by combining matches and semantic similarity
        score = len(degree_match) + len(years_of_exp_match) + avg_skills_similarity
        score /= (len(degrees_resume) + len(years_of_exp_resume) + 1)  # Add 1 to account for the average similarity
        semantic_scores.append(score)

        global unmatched_job_skills2
        unmatched_job_skills2 =[]
        # Append unmatched job skills to the global list
        for skills_resume in resume_skills:
            for skills_job_list in job_skills:
                for skills_job in skills_job_list:
                    if nlp(skills_resume).similarity(nlp(skills_job)) <= 0.7:
                        unmatched_job_skills2.append(skills_job)

    response = {
        'fulfillmentText': """Certainly. Here are the next three job postings for the position of {}:

1. {}, {}, {}, {}, {}, {}
2. {}, {}, {}, {}, {}, {}
3. {}, {}, {}, {}, {}, {}

Unfortunately, your current score does not meet the minimum requirement for these positions either. Based on our analysis, we have identified some skills that you are missing. Would you like me to suggest courses to help you improve your qualifications?
""".format(r['Job_title'],job_post_data['Company'][3],job_post_data['Title'][3], job_post_data['Location'][3],job_post_data['Salary'][3],job_post_data['Rating'][3],semantic_scores[0],job_post_data['Company'][4],job_post_data['Title'][4], job_post_data['Location'][4],job_post_data['Salary'][4],job_post_data['Rating'][4],semantic_scores[1],job_post_data['Company'][5], job_post_data['Title'][5],job_post_data['Location'][5],job_post_data['Salary'][5],job_post_data['Rating'][5],semantic_scores[2])
    }
    print(response)
    return jsonify(response), unmatched_job_skills2

@app.route('/c')
def course_suggest():
    skills1 = [item.lower() for item in unmatched_job_skills1] # make it lowercase
    skills2 = [item.lower() for item in unmatched_job_skills2]
    unmatched_job_skills = list(set(skills1 + skills2))

    # Append all unmatched job skills from the global list
    #urls = ['https://www.coursera.org/search?query=' + skill for skill in unmatched_job_skills]
    urls = ['www.coursera.com/' + skill for skill in unmatched_job_skills]

    response = {
    'fulfillmentText':"""Excellent. Based on your skills gap, I recommend the following courses:
- Courses: {}
Completing these courses and adding them to your resume can enhance your overall score and improve your chances of success in future applications. Best of luck!""".format(urls)
    }
    print(response)
    return jsonify(response)


if __name__ == "__main__":
    app.run(debug=True)

#response = requests.get(url)
#response = response.json ()
#print (response)