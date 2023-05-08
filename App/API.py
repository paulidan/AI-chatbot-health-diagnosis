import requests

infermedica = 'https://api.infermedica.com/v3/{}'


def _remote_titles(auth_string, case_id, language_model=None):
    app_id, app_key = auth_string.split(':')
    titles = {
        'Content-Type': 'application/json',
        'Dev-Mode': 'true',
        'Interview-Id': case_id,
        'app_id': '6e537823',
        'app_key': 'eb824288ad220a7449546f33eb567f53'}
    return titles


def endpoint_api(endpoint, auth_string, params, request_spec, case_id,
                  language_model=None):
    if auth_string and ':' in auth_string:
        url = infermedica.format(endpoint)
        titles = _remote_titles(auth_string, case_id, language_model)
    else:
        raise IOError('need App-Id:App-Key auth string')
    if language_model:
        titles['Language'] = lang_code
    if request_spec:
        resp = requests.post(
            url,
            params=params,
            json=request_spec,
            headers=titles)
    else:
        resp = requests.get(
            url,
            params=params,
            headers=titles)
    resp.raise_for_status()
    return resp.json()

# calling diagnosis-endpoint / input : patient_info / output: questions to be answered, list of diagnoses, "stop now"
def diagnosis_endpoint(proof, age, gender, case_id, auth_string, no_groups= True,
                   language_model=None):
    request_spec = {
        'age': age,
        'sex': gender,
        'evidence': proof,
        'extras': {
            # turn off group questions
            'disable_groups': no_groups
        }
    }
    return endpoint_api('diagnosis', auth_string, None, request_spec, case_id,
                         language_model)

# calling triage-endpoint / input : patient_info / output: questions to be answered, list of diagnoses, "stop now"
def triage_endpoint(proof, age, gender, case_id, auth_string, language_model=None):
    request_spec = {
        'age': age,
        'sex': gender,
        'evidence': proof
    }
    return endpoint_api('triage', auth_string, None, request_spec, case_id,
                         language_model)

# Processing text by NLP to capture observations
def parse(age, gender, text, auth_string, case_id, circumstances=(),
               conc_types=('symptom', 'risk_factor',), language_model=None):
    request_spec = {
       'age': age,
       'sex': gender,
       'text': text,
       'context': list(circumstances),
       'include_tokens': True,
       'concept_types': conc_types,
       }
    return endpoint_api('parse', auth_string, None, request_spec, case_id,
                         language_model=language_model)

# getting full lists of all symptoms and risk factors
def get_observation_titles(age, auth_string, case_id, language_model=None):
    obs_form = []
    obs_form.extend(
        endpoint_api('symptoms', auth_string,
                      {'age.value': age['value'], 'age.unit': age['unit']},
                      None, case_id=case_id, language_model=language_model))
    obs_form.extend(
        endpoint_api('risk_factors', auth_string,
                      {'age.value': age['value'], 'age.unit': age['unit']},
                      None, case_id=case_id, language_model=language_model))
    return {struct['id']: struct['name'] for struct in obs_form}

#  giving 'title' to every proof
def label_evidence(proof, titling):
    for example in proof:
        example['name'] = titling[example['id']]

# converting proof to expecting by API
def statement_to_evidence(report):
    return [{'id': r['id'], 'choice_id': r['choice_id'], 'source': 'initial'}
            for r in report]

# giving new id to answered question
def question_to_evidence(struct_item, obs_value):
    return [{'id': struct_item['id'],
             'choice_id': obs_value}]