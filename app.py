from openai import OpenAI
import streamlit as st

st.set_page_config(page_title='Streamlit Chat', page_icon='💬')
st.title('Interview Chatbot')

if 'setup_complete' not in st.session_state:
    st.session_state.setup_complete = False
if 'user_message_count' not in st.session_state:
    st.session_state.user_message_count = 0
if 'feedback_shown' not in st.session_state:
    st.session_state.feedback_shown = False
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'chat_complete' not in st.session_state:
    st.session_state.chat_complete = False


def complete_setup():
    st.session_state.setup_complete = True


def show_feedback():
    st.session_state.feedback_shown = True

def restart_interview():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

if not st.session_state.setup_complete:

    # Personal Details
    if 'name' not in st.session_state:
        st.session_state.name = ''
    if 'experience' not in st.session_state:
        st.session_state.experience = ''
    if 'skills' not in st.session_state:
        st.session_state.skills = ''

    st.subheader('Personal Information', divider='rainbow')

    st.text_input('Name', key='name',
                  placeholder='Enter your name', max_chars=40)
    st.text_area('Experience', key='experience',
                 placeholder='Describe your experience', height=None, max_chars=250)
    st.text_area('Skills', key='skills',
                 placeholder='List your skills', height=None, max_chars=250)

    st.write(f"**Name**: {st.session_state.name}")
    st.write(f"**Experience**: {st.session_state.experience}")
    st.write(f"**Skills**: {st.session_state.skills}")

    # Company Details
    st.subheader('Company and Position', divider='rainbow')

    if 'level' not in st.session_state:
        st.session_state['level'] = 'Junior'
    if 'position' not in st.session_state:
        st.session_state['position'] = 'Data Scientist'
    if 'company' not in st.session_state:
        st.session_state['company'] = 'Amazon'

    col1, col2 = st.columns(2)

    with col1:
        st.session_state['level'] = st.radio('Choose Level', options=[
                                             'Intern', 'Junior', 'Mid-level', 'Senior'])

    with col2:
        st.session_state['position'] = st.selectbox('Choose a Position', options=[
                                                    'Data Scientist', 'Data Engineer', 'ML Engineer', 'AI Engineer', 'Financial Analyst'])

    st.session_state['company'] = st.selectbox(
        'Select Company', ['Meta', 'Google', 'Amazon', 'Apple', 'Microsoft', 'Netflix'])

    st.write(
        f"**Your Information**: {st.session_state['level']} {st.session_state['position']} at {st.session_state['company']}")

    if st.button('Start Interview', on_click=complete_setup):
        st.write('Setup Complete! Starting Interview...')


if st.session_state.setup_complete and not st.session_state.feedback_shown and not st.session_state.chat_complete:

    st.info('''Start by Introducing yourself.''', icon='👋')

    # Create a ".streamlit" folder parallel to app.py and add a secrets.toml file with your API key
    client = OpenAI(
        api_key=st.secrets["GEMINI_API_KEY"],
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )

    if 'gemini_model' not in st.session_state:
        st.session_state['gemini_model'] = 'gemini-2.5-flash'

    if not st.session_state.messages:
        st.session_state.messages = [{'role': 'system', 'content': f"""
          You are an HR executive for the company {st.session_state['company']}. You are interviewing a user named {st.session_state['name']} for the position {st.session_state['position']} at level {st.session_state['level']}.
          The interviewee has the following experience: {st.session_state['experience']}.
          The interviewee possesses the following skills: {st.session_state['skills']}.

          Ask each question individually, creating a conversational flow rather than presenting all the questions simultaneously
          """}]

    for message in st.session_state.messages:
        if message['role'] != 'system':
            with st.chat_message(message['role']):
                st.markdown(message['content'])

    if st.session_state.user_message_count < 5:
        if prompt := st.chat_input('Your answer.', max_chars=1000):
            st.session_state.messages.append(
                {'role': 'user', 'content': prompt})
            with st.chat_message('user'):
                st.markdown(prompt)

            if st.session_state.user_message_count < 4:
                with st.chat_message('assistant'):
                    response = client.chat.completions.create(
                        model=st.session_state['gemini_model'],
                        messages=[
                            {'role': msg['role'], 'content': msg['content']}
                            for msg in st.session_state.messages
                        ],
                        stream=True
                    )
                    streamed_response = st.write_stream(response)
                st.session_state.messages.append(
                    {'role': 'assistant', 'content': streamed_response})

            st.session_state.user_message_count += 1

        if st.session_state.user_message_count >= 5:
            st.session_state.chat_complete = True

if st.session_state.chat_complete and not st.session_state.feedback_shown:
    if st.button('Get Feedback', on_click=show_feedback):
        st.write('Fetching feedback...')

if st.session_state.feedback_shown:
    st.subheader('Feedback', divider='rainbow')

    conversation_history = '\n'.join(
        [f"{msg['role']}: {msg['content']}" for msg in st.session_state.messages])

    feedback_client = OpenAI(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/", api_key=st.secrets["GEMINI_API_KEY"])

    feedback_completion = feedback_client.chat.completions.create(
        model=st.session_state['gemini_model'],
        messages=[
            {"role": "system",
             "content": """You are a helpful tool that provides feedback on an interviewee performance.
                Before the Feedback give a score of 1 to 10.
                Follow this format:
                Overal Score: //Your score
                Feedback: //Here you put your feedback
                Give only the feedback do not ask any additional questins.
                """
             },
            {
                'role': 'user',
                'content': f"This is the interview you need to evaluate. You are only a tool and shouldn't engage in conversation: {conversation_history}"
            }
        ]
    )

    st.write(feedback_completion.choices[0].message.content)

    if st.button('Restart Interview', type='primary'):
        restart_interview()
