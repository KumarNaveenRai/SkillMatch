import streamlit as st
import nltk
import spacy
import re
from PyPDF2 import PdfReader

nltk.download('stopwords')
spacy.load('en_core_web_sm')

import pandas as pd
import base64, random
import time, datetime
from streamlit_tags import st_tags
from PIL import Image
import pymysql
from courses import ds_course, web_course, android_course, ios_course, uiux_course, resume_videos, interview_videos
import os

os.environ["PAFY_BACKEND"] = "internal"

import pafy
import plotly.express as px
import yt_dlp

# Predefined skills list
skills_list = [
    "Python", "JavaScript", "HTML", "CSS", "React", "Node.js", "Machine Learning",
    "Data Analysis", "Photoshop", "InDesign", "WordPress", "SQL", "Flask", "Django"
]

# Define DB_table_name globally
DB_table_name = 'user_data'

# Fetch YouTube video title
def fetch_yt_video(link):
    try:
        ydl_opts = {
            'quiet': True,  # Suppress verbose output
            'noplaylist': True,  # Ensure only one video is processed
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(link, download=False)
            video_title = info_dict.get('title', 'Unknown Title')
            return video_title
    except Exception as e:
        print(f"Error fetching video info: {e}")
        return "Error: Unable to fetch video title"

# Generate download link for CSV
def get_table_download_link(df, filename, text):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'
    return href

# Extract text from PDF
def extract_resume_text(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        print(f"Error extracting text: {e}")
        return ""

# Extract name from resume text
def extract_name(text):
    lines = text.split('\n')
    for line in lines:
        # Skip lines with emails, phone numbers, or URLs
        if not re.search(r"[@+]|http", line):
            # Check if the line contains at least two words (first name and last name)
            if len(line.strip().split()) >= 2:
                return line.strip()
    return ""

# Extract email from resume text
def extract_email(text):
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    emails = re.findall(email_pattern, text)
    return emails[0] if emails else ""

# Extract phone number from resume text
def extract_phone(text):
    phone_pattern = r"\+?\d{0,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}"
    phones = re.findall(phone_pattern, text)
    return phones[0] if phones else ""

# Extract skills from resume text
def extract_skills(text, skills_list):
    extracted_skills = []
    for skill in skills_list:
        if re.search(rf"\b{skill}\b", text, re.IGNORECASE):
            extracted_skills.append(skill)
    return extracted_skills

# Parse resume text
def parse_resume(resume_text):
    name = extract_name(resume_text)
    email = extract_email(resume_text)
    phone = extract_phone(resume_text)
    skills = extract_skills(resume_text, skills_list)
    return name, email, phone, skills

# Display PDF in Streamlit
def show_pdf(file_path):
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

# Course recommender
def course_recommender(course_list):
    st.subheader("**Courses & Certificates🎓 Recommendations**")
    c = 0
    rec_course = []
    no_of_reco = st.slider('Choose Number of Course Recommendations:', 1, 10, 4)
    random.shuffle(course_list)
    for c_name, c_link in course_list:
        c += 1
        st.markdown(f"({c}) [{c_name}]({c_link})")
        rec_course.append(c_name)
        if c == no_of_reco:
            break
    return rec_course

# Database connection
def create_connection():
    try:
        connection = pymysql.connect(
            host='localhost',
            user='root',
            password='',  # Add your MySQL password here if required
            database='sra'  # Ensure the database exists
        )
        return connection
    except Exception as e:
        st.error(f"Error connecting to the database: {e}")
        return None

# Insert data into database
def insert_data(name, email, res_score, timestamp, no_of_pages, reco_field, cand_level, skills, recommended_skills, courses):
    connection = None  # Initialize connection variable
    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor()
            truncated_skills = skills[:500]  # Store only the first 500 characters
            print("Inserting Data Into Database...")  # Debugging
            print("Extracted Skills:", truncated_skills)  # Debugging

            insert_sql = f"INSERT INTO {DB_table_name} VALUES (0,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            rec_values = (name, email, str(res_score), timestamp, str(no_of_pages), reco_field, cand_level, truncated_skills, recommended_skills, courses)
            cursor.execute(insert_sql, rec_values)
            connection.commit()
            cursor.close()  # Close the cursor
    except Exception as e:
        st.error(f"Error inserting data into the database: {e}")
    finally:
        if connection:  # Ensure the connection is closed
            connection.close()

# Streamlit App
st.set_page_config(
    page_title="Smart Resume Analyzer",
    page_icon='./Logo/logo.jpg',
)

def run():


    # Streamlit UI
    st.title("SkillMatch Resume Analyzer")

    # Sidebar - User Selection
    st.sidebar.markdown("# Choose User")
    activities = ["Normal User", "Admin"]
    choice = st.sidebar.selectbox("Choose among the given options:", activities)

    # Load and Display Logo with Error Handling
    try:
        img = Image.open('./Logo/logo.jpg')  # Ensure the path is correct
        img = img.resize((250, 250))
        st.image(img)
    except FileNotFoundError:
        st.error("Logo image not found! Please check the path or upload the image.")

    # Database Connection
    try:
        connection = pymysql.connect(
            host="localhost",
            user="root",  # Change this as needed
            password="",  # Change this as needed
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor
        )
        cursor = connection.cursor()

        # Create Database
        db_sql = "CREATE DATABASE IF NOT EXISTS SRA;"
        cursor.execute(db_sql)
        connection.select_db("SRA")  # Switch to database

        # Create Table
        DB_table_name = "user_data"
        table_sql = f"""
            CREATE TABLE IF NOT EXISTS {DB_table_name} (
                ID INT NOT NULL AUTO_INCREMENT,
                Name VARCHAR(100) NOT NULL,
                Email_ID VARCHAR(50) NOT NULL,
                Resume_Score FLOAT NOT NULL,
                Timestamp VARCHAR(50) NOT NULL,
                Page_no INT NOT NULL,
                Predicted_Field VARCHAR(25) NOT NULL,
                User_Level VARCHAR(30) NOT NULL,
                Actual_Skills TEXT NOT NULL,
                Recommended_Skills TEXT NOT NULL,
                Recommended_Courses TEXT NOT NULL,
                PRIMARY KEY (ID)
            ) ENGINE=InnoDB;
        """
        cursor.execute(table_sql)
        connection.commit()  # Save changes

    except pymysql.Error as e:
        st.error(f"Database Error: {e}")

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()

    if choice == 'Normal User':
        pdf_file = st.file_uploader("Choose your Resume", type=["pdf"])
        if pdf_file is not None:
            save_image_path = './Uploaded_Resumes/' + pdf_file.name
            with open(save_image_path, "wb") as f:
                f.write(pdf_file.getbuffer())
            show_pdf(save_image_path)

            # Extract text from the PDF
            resume_text = extract_resume_text(save_image_path)

            # Parse resume text
            name, email, phone, skills = parse_resume(resume_text)

            # Display extracted details
            st.header("**Resume Analysis**")
            st.success(f"Hello {name}")
            st.subheader("**Your Basic info**")
            st.text(f'Name: {name}')
            st.text(f'Email: {email}')
            st.text(f'Phone: {phone}')
            st.text(f'Skills: {", ".join(skills)}')

            # Determine candidate level based on resume length
            no_of_pages = len(resume_text.split('\n')) // 50  # Approximate pages based on line count
            cand_level = ''
            if no_of_pages == 1:
                cand_level = "Fresher"
                st.markdown('''<h4 style='text-align: left; color: #d73b5c;'>You are looking Fresher.</h4>''',
                            unsafe_allow_html=True)
            elif no_of_pages == 2:
                cand_level = "Intermediate"
                st.markdown('''<h4 style='text-align: left; color: #1ed760;'>You are at intermediate level!</h4>''',
                            unsafe_allow_html=True)
            elif no_of_pages >= 3:
                cand_level = "Experienced"
                st.markdown('''<h4 style='text-align: left; color: #fba171;'>You are at experience level!''',
                            unsafe_allow_html=True)

            # Skill recommendations
            st.subheader("**Skills Recommendation💡**")
            keywords = st_tags(label='### Skills that you have',
                               text='See our skills recommendation',
                               value=skills, key='1')

            # Resume writing recommendation
            st.subheader("**Resume Tips & Ideas💡**")
            resume_score = 0
            if 'Objective' in resume_text:
                resume_score += 20
                st.markdown('''<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Objective</h4>''',
                            unsafe_allow_html=True)
            else:
                st.markdown('''<h4 style='text-align: left; color: #fabc10;'>[-] Add a career objective to give recruiters a clear idea of your goals.</h4>''',
                            unsafe_allow_html=True)

            if 'Declaration' in resume_text:
                resume_score += 20
                st.markdown('''<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Declaration</h4>''',
                            unsafe_allow_html=True)
            else:
                st.markdown('''<h4 style='text-align: left; color: #fabc10;'>[-] Add a declaration to assure recruiters of the authenticity of your resume.</h4>''',
                            unsafe_allow_html=True)

            if 'Hobbies' in resume_text or 'Interests' in resume_text:
                resume_score += 20
                st.markdown('''<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Hobbies</h4>''',
                            unsafe_allow_html=True)
            else:
                st.markdown('''<h4 style='text-align: left; color: #fabc10;'>[-] Add hobbies to showcase your personality.</h4>''',
                            unsafe_allow_html=True)

            if 'Achievements' in resume_text:
                resume_score += 20
                st.markdown('''<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Achievements</h4>''',
                            unsafe_allow_html=True)
            else:
                st.markdown('''<h4 style='text-align: left; color: #fabc10;'>[-] Add achievements to highlight your accomplishments.</h4>''',
                            unsafe_allow_html=True)

            if 'Projects' in resume_text:
                resume_score += 20
                st.markdown('''<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Projects</h4>''',
                            unsafe_allow_html=True)
            else:
                st.markdown('''<h4 style='text-align: left; color: #fabc10;'>[-] Add projects to demonstrate your practical experience.</h4>''',
                            unsafe_allow_html=True)

            # Display resume score
            st.subheader("**Resume Score📝**")
            st.markdown(
                """
                <style>
                    .stProgress > div > div > div > div {
                        background-color: #d73b5c;
                    }
                </style>""",
                unsafe_allow_html=True,
            )
            my_bar = st.progress(0)
            score = 0
            for percent_complete in range(resume_score):
                score += 1
                time.sleep(0.1)
                my_bar.progress(percent_complete + 1)
            st.success(f'** Your Resume Writing Score: {score} **')
            st.warning("** Note: This score is calculated based on the content you have added in your Resume. **")
            st.balloons()

            # Insert data into the database
            ts = time.time()
            cur_date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
            cur_time = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
            timestamp = str(cur_date + '_' + cur_time)

            insert_data(name, email, str(resume_score), timestamp, str(no_of_pages), "N/A", cand_level, ", ".join(skills), "N/A", "N/A")

            # Resume writing video2
            st.header("**Bonus Video for Resume Writing Tips💡**")
            resume_vid = random.choice(resume_videos)
            res_vid_title = fetch_yt_video(resume_vid)
            st.subheader("✅ **" + res_vid_title + "**")
            st.video(resume_vid)

            # Interview Preparation Video
            st.header("**Bonus Video for Interview👨‍💼 Tips💡**")
            interview_vid = random.choice(interview_videos)
            int_vid_title = fetch_yt_video(interview_vid)
            st.subheader("✅ **" + int_vid_title + "**")
            st.video(interview_vid)

        else:
            st.error('Please upload a valid PDF file.')
    else:
        st.success('Welcome to Admin Side')
        ad_user = st.text_input("Username")
        ad_password = st.text_input("Password", type='password')
        if st.button('Login'):
            if ad_user == 'admin' and ad_password == 'admin':
                st.success("Welcome Admin")
                connection = create_connection()
                if connection:
                    cursor = connection.cursor()
                    cursor.execute("SELECT * FROM user_data")
                    data = cursor.fetchall()
                    st.header("**User's Data**")
                    df = pd.DataFrame(data, columns=['ID', 'Name', 'Email', 'Resume Score', 'Timestamp', 'Total Page',
                                                     'Predicted Field', 'User Level', 'Actual Skills', 'Recommended Skills',
                                                     'Recommended Course'])
                    st.dataframe(df)
                    st.markdown(get_table_download_link(df, 'User_Data.csv', 'Download Report'), unsafe_allow_html=True)
                    query = 'SELECT * FROM user_data;'
                    plot_data = pd.read_sql(query, connection)
                    labels = plot_data.Predicted_Field.unique()
                    values = plot_data.Predicted_Field.value_counts()
                    st.subheader("📈 **Pie-Chart for Predicted Field Recommendations**")
                    fig = px.pie(df, values=values, names=labels, title='Predicted Field according to Skills')
                    st.plotly_chart(fig)
                    cursor.close()
                    connection.close()
            else:
                st.error("Wrong ID & Password Provided")

run()