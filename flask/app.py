import base64
from dotenv import load_dotenv
import os
from os import listdir
from os.path import isfile, join
import cv2
import shutil
import numpy as np
from flask import Flask, render_template, send_from_directory,request, jsonify
from flask_socketio import SocketIO, emit, join_room
from flask_cors import CORS
import mysql.connector
from mysql.connector import errorcode
from PIL import Image, ImageDraw, ImageFont
from collections import defaultdict
import numpy as np
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# .env 파일 불러오기
load_dotenv()

user = os.getenv('user')
password = os.getenv('password')
host = os.getenv('host')
database_name = os.getenv('database_name')
sql_file_path = os.getenv('sql_file_path')
cors_url_1 = os.getenv('CORS_URL_1')
cors_url_2 = os.getenv('CORS_URL_2')
korean_font_path = os.getenv('korean_font_path')

# ------------------------ ------- Database 유저 세팅 ------- ------------------------

# root계정 연결 -> flask 전용 유저 생성 및 연결

try:
    # MySQL 서버에 연결
    conn = mysql.connector.connect(
        host=host,
        user=user,
        password=password,  # 여기에 MySQL root 계정의 비밀번호를 입력하세요.
    )
    print("root 유저 연결 성공!")

    cursor = conn.cursor()
    cursor.execute("SHOW DATABASES")
    databases = [db[0] for db in cursor]

    if database_name in databases:
        print(f"{database_name} 데이터베이스가 이미 존재합니다.")
    else:
        cursor.execute(f"CREATE DATABASE {database_name}")
        print(f"{database_name} 데이터베이스를 생성하였습니다.")
    
    if conn.is_connected():
        cursor.close()
        conn.close()

    # MySQL 서버에 연결
    conn = mysql.connector.connect(
        host=host,
        user=user,
        password=password,  # 여기에 MySQL root 계정의 비밀번호를 입력하세요.
        database= database_name
    )
    print(f"{database_name} CONNECT 성공!")

    cursor = conn.cursor()

except mysql.connector.Error as err:
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        print("이름 또는 비밀번호가 잘못되었습니다.")
    elif err.errno == errorcode.ER_BAD_DB_ERROR:
        print("데이터베이스가 존재하지 않습니다.")
    else:
        print("연결에 실패하였습니다: {}".format(err))

# ------------------------ ------- Database SQL생성 ------- ------------------------

# SQL 파일 읽기
with open(sql_file_path, 'r') as file:
    sql_script = file.read()

# SQL 명령문을 개별적으로 분할
sql_commands = sql_script.split(';')

# 각 SQL 명령문 실행
for command in sql_commands:
    try:
        # 빈 명령문은 건너뛰기
        if not command.strip():
            continue

        cursor.execute(command)
        # 결과 처리
        if cursor.with_rows:
            print("> SELECT / SQL문 실행. : \n> statement : \n{}".format(command))
            print(cursor.fetchall())
        else:
            print("> UPDATE / SQL문 실행. \n> statement : \n{} \n> rowcount : {}".format(
                command, cursor.rowcount))
        print("> Statement executed successfully :) \n")
    except mysql.connector.Error as err:
        print("> Error executing statement :\n{}\n> 에러메시지 : {}".format(command, err))

# 변경사항 적용
conn.commit()

print(">> Database schema setting complete! :) ")

# ------------------------ ------- 얼굴 인식 ------- ------------------------

# 검색 결과 처리
users_models = []
face_classifier = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
# 유저별 face_detected_count 딕셔너리 초기화    
user_counts = {}


def createFolder(directory):
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
    except OSError: 
        print ('Error: Creating directory. ' + directory)

def base64_to_image(base64_string):
    """
    The base64_to_image function accepts a base64 encoded string and returns an image.
    The function extracts the base64 binary data from the input string, decodes it, converts 
    the bytes to numpy array, and then decodes the numpy array as an image using OpenCV.
    
    :param base64_string: Pass the base64 encoded image string to the function
    :return: An image
    """
    base64_data = base64_string.split(",")[1]
    image_bytes = base64.b64decode(base64_data)
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    return image

def face_detector(img, size = 0.5):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_classifier.detectMultiScale(gray,1.3,5,minSize=(210,210)) #얼굴 최소 크기. 이것보다 작으면 무시

    if faces is():
        return img,[]

    for(x,y,w,h) in faces:
        cv2.rectangle(img, (x,y),(x+w,y+h),(0,255,255),2)
        roi = img[y:y+h, x:x+w]
        roi = cv2.resize(roi, (200,200))

    return img,roi

def load_user_models(cursor):
    """
    Load user models from the database and add them to the global users_models list.
    :param cursor: Database cursor to execute the query
    """
    global users_models

    # 모든 사용자의 모델 데이터와 이름 검색
    fetch_models_query = "SELECT user_name, user_face_model FROM User"
    cursor.execute(fetch_models_query)

    # 검색 결과 처리
    for (user_name, model_data) in cursor.fetchall():
        temp_model_path = f"temp_model_{user_name}.yml"
        with open(temp_model_path, "wb") as file:
            file.write(model_data)

        # 모델 로드
        model = cv2.face.LBPHFaceRecognizer_create()
        model.read(temp_model_path)

        # 모델과 사용자 이름을 튜플로 묶어 리스트에 추가
        users_models.append((user_name, model))

        # 로드된 임시 파일 삭제
        os.remove(temp_model_path)

    # 사용자 모델 로드 확인
    for user_name, model in users_models:
        print(f"Model for {user_name} loaded.")



load_user_models(cursor)
createFolder('./temp')

# ------------------------ ------- Flask서버 셋팅 ------- ------------------------

app = Flask(__name__, static_folder="./templates/static")
CORS(app, origins=[cors_url_1, cors_url_2])

socketio = SocketIO(app, cors_allowed_origins="*")

def is_valid_phone_number(phone_number):
    # 전화번호 유효성 검사 로직 구현 (여기서는 간단한 형식 체크만 하겠습니다)
    import re
    pattern = re.compile(r'^01([0|1|6|7|8|9]?)-?([0-9]{4})-?([0-9]{4})$')
    return pattern.match(phone_number)

def putTextWithKorean(image, text, position, font_path, font_size, color):
    image_pil = Image.fromarray(image)
    draw = ImageDraw.Draw(image_pil)
    font = ImageFont.truetype(font_path, font_size)
    draw.text(position, text, font=font, fill=color)
    return np.array(image_pil)

@socketio.on("connect")
def handle_connect():
    user_id = request.args.get('user_id')
    join_room(user_id)
    print(f"Client {user_id} connected.")



@socketio.on("image")
def receive_image(image):
    # Decode the base64-encoded image data
    face = cv2.flip(base64_to_image(image), 1)
    image, face = face_detector(face)
    try:
        face = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)

        # 초기화: 가장 높은 예측값을 찾기 위한 변수들
        highest_confidence = 0
        recognized_user_name = ""

        # users_models 리스트를 순회하며 얼굴 인식 시도
        for user_name, model in users_models:
            result = model.predict(face)
            confidence = int(100 * (1 - (result[1]) / 300))

            # 가장 높은 예측값 찾기
            if confidence > highest_confidence:
                highest_confidence = confidence
                recognized_user_name = user_name

        # 가장 높은 예측값을 가진 사용자의 정보 표시
        if highest_confidence > 75:
            image = putTextWithKorean(image, f"Unlocked: {recognized_user_name} / {highest_confidence}", (75, 200), korean_font_path, 20, (0, 255, 0))
        else:
            image = putTextWithKorean(image, "Locked", (75, 200), korean_font_path, 20, (0, 0, 255))

    except:
        image = putTextWithKorean(image, "Face Not Found", (75, 200), korean_font_path, 20, (255, 0, 0))

    # 이미지 처리 및 송출
    frame_resized = cv2.resize(image, (640, 360))
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
    result, frame_encoded = cv2.imencode(".jpg", frame_resized, encode_param)
    processed_img_data = base64.b64encode(frame_encoded).decode()
    b64_src = "data:image/jpg;base64,"
    processed_img_data = b64_src + processed_img_data
    emit("processed_image", processed_img_data)

@socketio.on('upload_image')
def handle_image_upload(data):
    user_id = data['user_id']
    image_data = data['image']

    face = cv2.flip(base64_to_image(image_data), 1)
    image, face = face_detector(face)
    try:
        # face = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
        print("x")
        # 이미지를 임시 저장소에 저장
        save_temp_image(user_id, face)

        _, buffer = cv2.imencode('.jpg', image)
        processed_image = base64.b64encode(buffer).decode('utf-8')
        emit("image_processed", f"data:image/jpeg;base64,{processed_image}", room=user_id)

        # 30장의 사진이 모였는지 확인
        if is_30_images_collected(user_id):
            # 예측값 집계
            predictions = predict_user(user_id)
            
            # 가장 많이 예측된 사용자 이름 찾기
            most_common_user, _ = max(predictions.items(), key=lambda item: item[1])
            
            # 클라이언트에 결과 반환
            emit('user_recognized', {'user_name': most_common_user}, room=user_id)

            # 임시 저장소 정리
            clear_temp_storage(user_id)
    except Exception as e:
        print(f"Error: {e}")

# 예측 집계 함수
def predict_user(user_id):
    load_user_models(cursor)
    predictions = defaultdict(int)
    for image in load_temp_images(user_id):
        highest_confidence = 0
        recognized_user_name = ""
        for user_name, model in users_models:
            result = model.predict(image)
            confidence = int(100 * (1 - (result[1]) / 300))
            if confidence > highest_confidence:
                highest_confidence = confidence
                recognized_user_name = user_name
        if highest_confidence > 75:  # 예시로 75%를 기준으로 설정
            predictions[recognized_user_name] += 1
    return predictions

TEMP_IMAGE_DIR = "temp_images"

def create_user_temp_dir(user_id):
    user_dir = os.path.join(TEMP_IMAGE_DIR, user_id)
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)

def save_temp_image(user_id, image):
    create_user_temp_dir(user_id)
    user_dir = os.path.join(TEMP_IMAGE_DIR, user_id)
    image_count = len(os.listdir(user_dir))
    cv2.imwrite(os.path.join(user_dir, f"img_{image_count + 1}.jpg"), image)

def is_30_images_collected(user_id):
    user_dir = os.path.join(TEMP_IMAGE_DIR, user_id)
    return len(os.listdir(user_dir)) >= 30

def clear_temp_storage(user_id):
    user_dir = os.path.join(TEMP_IMAGE_DIR, user_id)
    if os.path.exists(user_dir):
        for file in os.listdir(user_dir):
            os.remove(os.path.join(user_dir, file))
        os.rmdir(user_dir)

def load_temp_images(user_id):
    user_dir = os.path.join(TEMP_IMAGE_DIR, user_id)
    images = []
    if os.path.exists(user_dir):
        for file in sorted(os.listdir(user_dir)):
            img_path = os.path.join(user_dir, file)
            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            images.append(img)
    return images

@socketio.on("data_for_storage")
def receive_data(data):
    image = data.get("image")
    phone_number = data.get("phoneNumber")
    name = data.get("name")

    # 유저가 처음 데이터를 보내는 경우, 딕셔너리에 초기값 0 설정
    if phone_number not in user_counts:
        user_counts[phone_number] = 0

    # global face_detected_count
    try:
        # Decode the base64-encoded image data
        face = base64_to_image(image)
        image, roi = face_detector(face)  # roi는 사용하지 않으므로 무시합니다.
        if len(roi) > 0: #얼굴이 1개 이상 검출 시,
            # Face detected, increment the count
            # face_detected_count 증가
            user_counts[phone_number] += 1
            if user_counts[phone_number] <= 100:
                print(str(user_counts[phone_number]) + " + " + phone_number)
                # Optionally, emit the processed image with face boxes back to the client
                _, buffer = cv2.imencode('.jpg', image)
                processed_image = base64.b64encode(buffer).decode('utf-8')
                emit("processed_image", f"data:image/jpeg;base64,{processed_image}")
                # Save the image to the server
                createFolder(f'./temp/{phone_number}')
                cv2.imwrite(f'./temp/{phone_number}/{user_counts[phone_number]}.jpg', roi)
                # Optionally, emit a message indicating a successful save
                # emit("image_saved", {"count": face_detected_count})
            else:
                # If 100 images have been saved, you can emit a message to stop sending images
                emit("stop_sending", {"message": "100 face images have been saved"})

                # 모델 100장 학습 시키고
                data_path = f'./temp/{phone_number}/'
                onlyfiles = [f for f in listdir(data_path) if isfile(join(data_path,f))]

                Training_Data, Labels = [], []

                for i, files in enumerate(onlyfiles):
                    image_path = data_path + onlyfiles[i]
                    images = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
                    Training_Data.append(np.asarray(images, dtype=np.uint8))
                    Labels.append(i)

                Labels = np.asarray(Labels, dtype=np.int32)

                model = cv2.face.LBPHFaceRecognizer_create()

                model.train(np.asarray(Training_Data), np.asarray(Labels))
                # 모델 저장
                model.save(f'./temp/{phone_number}/trained_model_{phone_number}.yml')

                print(f"{phone_number}'s Model Training Complete!!!!!")

                # 전달받은 유저 아이디에 매핑되게 디비에 저장
                try:
                    # 모델 파일을 이진 형식으로 읽기
                    with open(f'./temp/{phone_number}/trained_model_{phone_number}.yml', 'rb') as file:
                        model_data = file.read()

                    # 데이터베이스에 사용자 정보와 모델 데이터 저장
                    insert_user_query = "INSERT INTO User (user_id, user_name, phoneNumber, user_face_model) VALUES (UUID(), %s, %s, %s)"
                    cursor.execute(insert_user_query, (name, phone_number, model_data))
                    conn.commit()

                    print(f"> User {name} with phone number {phone_number} has been successfully registered.")
                    emit("registration_success", {"message": f"User {name} registered successfully"})

                except Exception as e:
                    print(f"> An error occurred during user registration: {e}")
                    emit("registration_failed", {"error": str(e)})

                # 경로에 있는 이미지와 경로 삭제
                temp_path = f'./temp/{phone_number}'
                shutil.rmtree(temp_path)
                print(f"Images and directory {temp_path} have been deleted")
                # 등록완료!
                
        else:
            # No face detected, optionally emit a message indicating failure to detect a face
            emit("face_not_detected", {"message": "No face detected in the image"})
    except Exception as e:
        print(f"An error occurred: {e}")

@app.route('/register', methods=['POST'])
def register_user():
    data = request.get_json()
    name = data.get('name')
    phone_number = data.get('phoneNumber')

    print("> name : " + name)
    print("> phone_number : " + phone_number)

    # 전화번호 중복 체크
    query = "SELECT * FROM `User` WHERE `phoneNumber` = %s"
    cursor.execute(query, (phone_number,))
    result = cursor.fetchone()

    if result:
        return {"error": "Phone number already registered"}, 400

    # Your code to add the new user to the database goes here
    # ...

    # 유효성 검사 (예: 전화번호 형식 검사)
    if not is_valid_phone_number(phone_number):
        # 유효하지 않은 전화번호 형식이면 실패 응답을 보냅니다.
        return {"error": "Invalid phone number"}, 400

    # 성공 응답을 보냅니다.
    return jsonify({'status': 'success', 'name': name, 'phoneNumber': phone_number})

@app.route("/")
def index():
    """
    The index function returns the index.html template, which is a landing page for users.
    
    :return: The index
    """
    return render_template("index.html")


if __name__ == "__main__":
    try:
        socketio.run(app, debug=False, port=5001, host='0.0.0.0')
    except Exception as e:  # Catch all exceptions
        print(f"An error occurred: {e}")


