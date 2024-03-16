import json
import os

import boto3

import streamlit as st
from streamlit.web.server.websocket_headers import _get_websocket_headers

# 環境変数を取得
cognito_region = os.environ["COGNITO_REGION"]
cognito_identity_id = os.environ["COGNITO_IDENTITY_ID"]
cognito_userpool_id = os.environ["COGNITO_USERPOOL_ID"]
cognito_client_id = os.environ["COGNITO_CLIENT_ID"]
cognito_hosted_ui_domain = os.environ["COGNITO_HOSTED_UI_DOMAIN_PREFIX"]

logout_uri = os.environ["SIGNOUT_URL"]


def sign_out_url():
    return f"https://{cognito_hosted_ui_domain}.auth.{cognito_region}.amazoncognito.com/logout?client_id={cognito_client_id}&logout_uri={logout_uri}"


def get_credentials():
    headers = _get_websocket_headers()

    authorization = headers["Authorization"]
    id_token = authorization.replace("Bearer ", "")

    client = boto3.client("cognito-identity", region_name=cognito_region)

    cognito_idp_name = (
        f"cognito-idp.{cognito_region}.amazonaws.com/{cognito_userpool_id}"
    )

    response = client.get_id(
        IdentityPoolId=cognito_identity_id, Logins={cognito_idp_name: id_token}
    )

    identity_id = response["IdentityId"]

    response = client.get_credentials_for_identity(
        IdentityId=identity_id,
        Logins={cognito_idp_name: id_token},
    )

    return response["Credentials"]


def create_bedrock_runtime_client():
    credentials = get_credentials()
    client = boto3.Session(
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretKey"],
        aws_session_token=credentials["SessionToken"],
        region_name="us-east-1",
    ).client("bedrock-runtime")
    return client


def stream(stream: dict):
    for event in stream.get("body"):
        chunk = json.loads(event["chunk"]["bytes"])
        if "delta" in chunk and "text" in chunk["delta"]:
            yield chunk["delta"]["text"]


st.title("Bedrock チャット")

st.link_button("Sign out", sign_out_url())


if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"][0]["text"])

if prompt := st.chat_input("何でも聞いてください。"):
    st.session_state.messages.append(
        {
            "role": "user",
            "content": [{"type": "text", "text": prompt}],
        }
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    client = create_bedrock_runtime_client()

    response = client.invoke_model_with_response_stream(
        modelId="anthropic.claude-3-haiku-20240307-v1:0",
        body=json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 300,
                "system": "あなたは優秀なAIボットです",
                "messages": st.session_state.messages,
            }
        ),
    )

    with st.chat_message("assistant"):
        result = st.write_stream(stream(response))

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": [{"type": "text", "text": result}],
        }
    )
