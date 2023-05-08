import sys
import API
import re
import constant

class AmbiguousAnswerException(Exception):
    pass

# display prompt and this method read user input
def read_input(prompt):
    if prompt.endswith('?'):
        prompt = prompt + ' '
    else:
        prompt = prompt + ': '
    print(prompt, end='', flush=True)
    return sys.stdin.readline().strip()

# This method reads age and gender from the patient
def read_patient_info():
    response = read_input("How old are you and what is your gender? (e.g., 23 female)")
    try:
        age = int(check_age(response))
        gender = check_gender(response, constant.GENDER)
        if age < constant.LOW_AGE:  
            raise ValueError("Ages below 12 are not supported yet.")
        if age > constant.HIGH_AGE:
            raise ValueError("We only support till 130 years old.")
    except (AmbiguousAnswerException, ValueError) as e:
        print("{} Could you please repeat?".format(e))
        return read_patient_info()
    return age, gender

# This communicates with the front-end
def read_patient_info_new(response):
    # response = read_input("How old are you and what is your gender? (e.g., 23 female)")
    # try:
    age = int(check_age(response))
    gender = check_gender(response, constant.GENDER)
    if age < constant.LOW_AGE:  
        raise ValueError("Ages below 12 are not supported yet.")
    if age > constant.HIGH_AGE:
        raise ValueError("We only support till 130 years old.")
    # except (AmbiguousAnswerException, ValueError) as e:
    #     print("{} Could you please repeat?".format(e))
    #     return read_patient_info()
    return age, gender

# checking gender
def check_gender(sentence, mapping):
    gender_keywords = set(remove_keywords(sentence, mapping.keys()))
    if len(gender_keywords) == 1:
        return mapping[gender_keywords.pop().lower()]
    elif len(gender_keywords) > 1:
        raise AmbiguousAnswerException("Too many genders")
    else:
        raise ValueError("No gender found.")

# checking age 
def check_age(sentence):
    age = set(re.findall(r"\b\d+\b", sentence))
    if len(age) == 1:
        return age.pop()
    elif len(age) > 1:
        raise AmbiguousAnswerException("Too many ages")
    else:
        raise ValueError("No age found.")

# Method for reading input and sending info to API
def read_send_complaint(age, gender, auth_string, case_id, circumstances, language_model=None):
    sentence = read_input('Please describe you complaints')
    if not sentence:
        return None
    answ = API.parse(age, gender, sentence, auth_string, case_id, circumstances,
                                language_model=language_model)
    return answ.get('mentions', [])

# This method is formatting complains into simple notes
def raise_mentions(mention):
    answer_sign = {"present": "✔︎ ", "absent": "✗ ", "unknown": "? "}
    title = mention["name"]
    sign = answer_sign[mention["choice_id"]]
    return "{}{}".format(sign, title)

# this method return id of present complains
def id_complains(report):
    return [r['id'] for r in report if r['choice_id'] == 'present']

# printing all the notes
def summarise_mentions(report):
    return "{}".format(", ".join(raise_mentions(r) for r in report))

# This method will keep asking questions until user will send an empty message
def read_complaints(age, gender, auth_string, case_id, language_model=None):
    report = []
    circumstances = []  # list of ids of present symptoms 
    while True:
        portion = read_send_complaint(age, gender, auth_string, case_id, circumstances,
                                         language_model=language_model)
        if portion:
            summarise_mentions(portion)
            report.extend(portion)
            # remember the mentions
            circumstances.extend(id_complains(portion))

        # empty message but got at least one complaint
        if report and portion is None:
            return report

# this method is to understand single questions where user can answer yes/no/dont know
def read_question_response(question_text):
    response = read_input(question_text)
    if not response:
        return None
    try:
        return make_decision(response, constant.RESPONSE)
    except (AmbiguousAnswerException, ValueError) as e:
        print("{} Could you please repeat?".format(e))
        return read_question_response(question_text)

# asks about complaing untill user gives an empty answer or API stops
def interview(proof, age, gender, case_id, auth, language_model=None):
    while True:
        answ = API.diagnosis_endpoint(proof, age, gender, case_id, auth,
                                        language_model=language_model)
        question_type = answ['question']
        diagnoses = answ['conditions']
        should_stop_now = answ['should_stop']
        if should_stop_now:
            # call it now and return all the information together.
            triage_resp = API.triage_endpoint(proof, age, gender, case_id,
                                                auth,
                                                language_model=language_model)
            return proof, diagnoses, triage_resp
        new_evidence = []
        if question_type['type'] == 'single':
            # only single question type
            question_items = question_type['items']
            assert len(question_items) == 1  # this is a single question
            question_item = question_items[0]
            obs_value = read_question_response(
                question_text=question_type['text'])
            if obs_value is not None:
                new_evidence.extend(API.question_to_evidence(
                    question_item, obs_value))
        else:
            raise NotImplementedError("Unfortunately group questions were not implemented yet...")
        proof.extend(new_evidence)

# summarising patient statement and given answers only 
def summarise_part_evidence(proof, header):
    print(header + ':')
    for idx, piece in enumerate(proof):
        print('{:2}. {}'.format(idx + 1, raise_mentions(piece)))
    print()

# summarising ALL of the evidence 
def summarise_everything(proof):
    described = []
    answered = []
    for piece in proof:
        (described if piece.get('initial') else answered).append(piece)
    summarise_part_evidence(described, 'Patient statement:')
    summarise_part_evidence(answered, 'Given answers:')

# summarising diagnoses and printing them
def summarise_diagnoses(diagnoses):
    diagnosis_str = 'Your diagnoses are:'
    print('Your diagnoses are:')
    for idx, diag in enumerate(diagnoses):
        print('{:2}. {:.2f} {}'.format(idx + 1, diag['probability'],
                                       diag['name']))
        diagnosis_str += '\n{:2}. {:.2f} {}'.format(idx + 1, diag['probability'],
                                       diag['name'])
    diagnosis_str += "\n"
    print()
    return diagnosis_str

# summarise triage and printing them
def summarise_triage(triage_resp):
    triage_str = 'What you should do?: {}'.format(triage_resp['triage_level']) 
    print('What you should do?: {}'.format(triage_resp['triage_level']))
    teleconsultation_applicable = triage_resp.get(
        'teleconsultation_applicable')
    if teleconsultation_applicable is not None:
        print('Do you need teleconsultation?: {}'
              .format(teleconsultation_applicable))
        triage_str += 'Do you need teleconsultation?: {}\n'.format(teleconsultation_applicable)
    print()
    return triage_str

# remove keywords from text, args: text as string, and keywords as list, 
# return all keywords as list
def remove_keywords(sentence, keywords):
    pattern = r"|".join(r"\b{}\b".format(re.escape(keyword))
                        for keyword in keywords)
    report_regex = re.compile(pattern, flags=re.I)
    return report_regex.findall(sentence)

# make decision keywords from text, args: text as string, and mapping as dictionary
# return single decision as string. if string containsmapping, raise error
def make_decision(sentence, mapping):
    decision_keywrods = set(remove_keywords(sentence, mapping.keys()))
    if len(decision_keywrods) == 1:
        return mapping[decision_keywrods.pop().lower()]
    elif len(decision_keywrods) > 1:
        raise AmbiguousAnswerException("The decision seemed ambiguous.")
    else:
        raise ValueError("No decision found.")

