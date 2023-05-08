import argparse
import uuid

import consultation
import API

# to start application type in terminal % python3 mainchat.py 6e537823:eb824288ad220a7449546f33eb567f53

# retriving authentisaction string from typed text in terminal
def get_auth_string(authen):
    if ":" in authen:
        return authen
    try:
        with open(authen) as stream:
            content = stream.read()
            content = content.strip()
            if ":" in content:
                return content
    except FileNotFoundError:
        pass
    raise ValueError(authen)

# return authentication credentials and chosen language
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-auth",
                        help="what is your APP_ID and APP_KEY?"
                             "type APP_ID:APP_KEY")
    parser.add_argument("--model",
                        help="what language do you want to use?"
                             "type for example: infermedica-pl")
    args = parser.parse_args()
    return args

# new id
def new_session():
    return uuid.uuid4().hex


def run():
    # args = parse_args()
    # auth_string = get_auth_string(args.auth)
    # patient = new_session()

    # read required patient info
    age, gender = consultation.read_patient_info()
    print(f"Patient is: {age} year old {gender}.")
    age = {'value':  age, 'unit': 'year'}
    
    # query for observation names and storing them
    titling = API.get_observation_titles(age, auth_string, patient, args.model)

    # read complaints
    report = consultation.read_complaints(age, gender, auth_string, patient, args.model)

    # keep asking
    proof = API.statement_to_evidence(report)
    proof, diagnoses, triage = consultation.interview(proof, age,
                                                    gender, patient,
                                                    auth_string,
                                                    args.model)
    API.label_evidence(proof, titling)

    # printing all information about the patient.
    print()
    consultation.summarise_everything(proof)
    consultation.summarise_diagnoses(diagnoses)
    consultation.summarise_triage(triage)


if __name__ == "__main__":
    run()