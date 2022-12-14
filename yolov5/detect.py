import argparse
import os
import platform
import sys
from pathlib import Path
from tensorflow import keras
import torch
from time import time, gmtime
from PIL import Image, ImageOps
import numpy as np
import cv2
from time import strftime
from flask import Flask, render_template, render_template_string, Response, request, redirect, jsonify, session, url_for
app = Flask(__name__)
from flask_sqlalchemy import SQLAlchemy
from multiprocessing import Process,Lock
from threading import Thread, Lock
from sqlalchemy import desc, cast, Date
import json
from flask_models.Image import db, Image
from datetime import datetime
import glob
from sqlalchemy.sql import func
from keras.preprocessing.image import ImageDataGenerator
from keras.callbacks import  EarlyStopping
from keras.models import Sequential
from keras import layers
from keras.layers import Conv2D,MaxPool2D,Flatten,Dense


from models.common import DetectMultiBackend
from utils.dataloaders import IMG_FORMATS, VID_FORMATS, LoadImages, LoadScreenshots, LoadStreams
from utils.general import (LOGGER, Profile, check_file, check_img_size, check_imshow, check_requirements, colorstr, cv2,
                           increment_path, non_max_suppression, print_args, scale_boxes, strip_optimizer, xyxy2xywh)
from utils.plots import Annotator, colors, save_one_box
from utils.torch_utils import select_device, smart_inference_mode

from time import sleep

app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:1234@localhost:3306/test"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
db.app = app
with app.app_context():
    db.create_all()

global response_img
response_img = (b'--frame\r\n'
                            b'Content-Type: image/jpeg\r\n\r\n' + open('t.jpg', 'rb').read() + b'\r\n')


lock = Lock()

now_path = os.getcwd()
captured = False
src = 1
start_stream = int(time())
previous = ""
dog_action=""
dog_actions = {0:"eating", 1:"running", 2:"yawn", 3: "standing", 4:"sitting", 5:"kneeldown"}
dog_act_detect_model = keras.models.load_model('keras_model.h5')
dog_image = 0
FILE = Path(__file__).resolve()
ROOT = FILE.parents[0]  # YOLOv5 root directory
two_dogs = False
dog_name = "dog"
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))  # add ROOT to PATH
ROOT = Path(os.path.relpath(ROOT, Path.cwd()))  # relative
two_dog_labels = [0,0]

def get_video():
    while True:
        yield response_img
        sleep(0.05)


already_loaded = False
@smart_inference_mode()
def run(
        weights=ROOT / 'pretrained/dogs.pt',  # model path or triton URL
        source=ROOT / 'data/images',  # file/dir/URL/glob/screen/0(webcam)
        data=ROOT / 'data/coco128.yaml',  # dataset.yaml path
        imgsz=(640, 640),  # inference size (height, width)
        conf_thres=0.25,  # confidence threshold
        iou_thres=0.45,  # NMS IOU threshold
        max_det=1000,  # maximum detections per image
        device='',  # cuda device, i.e. 0 or 0,1,2,3 or cpu
        view_img=False,  # show results
        save_txt=False,  # save results to *.txt
        save_conf=False,  # save confidences in --save-txt labels
        save_crop=False,  # save cropped prediction boxes
        nosave=False,  # do not save images/videos
        classes=None,  # filter by class: --class 0, or --class 0 2 3
        agnostic_nms=False,  # class-agnostic NMS
        augment=False,  # augmented inference
        visualize=False,  # visualize features
        update=False,  # update all models
        project=ROOT / 'runs/detect',  # save results to project/name
        name='exp',  # save results to project/name
        exist_ok=False,  # existing project/name ok, do not increment
        line_thickness=3,  # bounding box thickness (pixels)
        hide_labels=False,  # hide labels
        hide_conf=False,  # hide confidences
        half=False,  # use FP16 half-precision inference
        dnn=False,  # use OpenCV DNN for ONNX inference
        vid_stride=1,  # video frame-rate stride
):
    global two_dogs
    dog_name_model = 0
    global already_loaded
    if two_dogs and not already_loaded:
        dog_name_model = keras.models.load_model('two_dogs.h5')
        already_loaded = True
    source = str(source)
    save_img = not nosave and not source.endswith('.txt')  # save inference images
    is_file = Path(source).suffix[1:] in (IMG_FORMATS + VID_FORMATS)
    is_url = source.lower().startswith(('rtsp://', 'rtmp://', 'http://', 'https://'))
    webcam = source.isnumeric() or source.endswith('.txt') or (is_url and not is_file)
    screenshot = source.lower().startswith('screen')
    if is_url and is_file:
        source = check_file(source)  # download
    # Directories
    save_dir = increment_path(Path(project) / name, exist_ok=exist_ok)  # increment run
    (save_dir / 'labels' if save_txt else save_dir).mkdir(parents=True, exist_ok=True)  # make dir

    # Load model
    device = select_device(device)
    model = DetectMultiBackend(weights, device=device, dnn=dnn, data=data, fp16=half)
    stride, names, pt = model.stride, model.names, model.pt
    imgsz = check_img_size(imgsz, s=stride)  # check image size

    # Dataloader
    bs = 1  # batch_size
    if webcam:
        view_img = check_imshow()
        dataset = LoadStreams(source, img_size=imgsz, stride=stride, auto=pt, vid_stride=vid_stride)
        bs = len(dataset)
    elif screenshot:
        dataset = LoadScreenshots(source, img_size=imgsz, stride=stride, auto=pt)
    else:
        dataset = LoadImages(source, img_size=imgsz, stride=stride, auto=pt, vid_stride=vid_stride)
    vid_path, vid_writer = [None] * bs, [None] * bs

    # Run inference
    model.warmup(imgsz=(1 if pt or model.triton else bs, 3, *imgsz))  # warmup
    seen, windows, dt = 0, [], (Profile(), Profile(), Profile())
    global previous

    global dog_action
    for path, im, im0s, vid_cap, s in dataset:

        with dt[0]:
            im = torch.from_numpy(im).to(model.device)
            im = im.half() if model.fp16 else im.float()  # uint8 to fp16/32
            im /= 255  # 0 - 255 to 0.0 - 1.0
            if len(im.shape) == 3:
                im = im[None]  # expand for batch dim

        # Inference
        with dt[1]:
            visualize = increment_path(save_dir / Path(path).stem, mkdir=True) if visualize else False
            pred = model(im, augment=augment, visualize=visualize)

        # NMS
        with dt[2]:
            pred = non_max_suppression(pred, conf_thres, iou_thres, classes, agnostic_nms, max_det=max_det)

        # Second-stage classifier (optional)
        # pred = utils.general.apply_classifier(pred, classifier_model, im, im0s)

        # Process predictions

        for i, det in enumerate(pred):  # per image
            global captured
            seen += 1
            if webcam:  # batch_size >= 1
                p, im0, frame = path[i], im0s[i].copy(), dataset.count
                s += f'{i}: '
            else:
                p, im0, frame = path, im0s.copy(), getattr(dataset, 'frame', 0)

            p = Path(p)  # to Path
            save_path = str(save_dir / p.name)  # im.jpg
            txt_path = str(save_dir / 'labels' / p.stem) + ('' if dataset.mode == 'image' else f'_{frame}')  # im.txt
            s += '%gx%g ' % im.shape[2:]  # print string
            gn = torch.tensor(im0.shape)[[1, 0, 1, 0]]  # normalization gain whwh
            imc = im0.copy() if save_crop else im0  # for save_crop
            annotator = Annotator(im0, line_width=line_thickness, example=str(names))
            global dog_image
            dog_image = im0.copy()
            global dog_name
            if len(det):
                # Rescale boxes from img_size to im0 size
                det[:, :4] = scale_boxes(im.shape[2:], det[:, :4], im0.shape).round()
            

                # Print results
                for c in det[:, 5].unique():
                    n = (det[:, 5] == c).sum()  # detections per class
                    s += f"{n} {names[int(c)]}{'s' * (n > 1)}, "  # add to string

                # Write results
                for *xyxy, conf, cls in reversed(det):
                    if save_txt:  # Write to file
                        xywh = (xyxy2xywh(torch.tensor(xyxy).view(1, 4)) / gn).view(-1).tolist()  # normalized xywh
                        line = (cls, *xywh, conf) if save_conf else (cls, *xywh)  # label format
                        with open(f'{txt_path}.txt', 'a') as f:
                            f.write(('%g ' * len(line)).rstrip() % line + '\n')

                    if save_img or save_crop or view_img:  # Add bbox to image
                        xywh = (xyxy2xywh(torch.tensor(xyxy).view(1, 4)) / gn).view(-1).tolist()  # normalized xywh
                        c = int(cls)  # integer class

                        shape_y,shape_x,cha = dog_image.shape
                        x_min = int((xywh[0] - xywh[2]/2) * shape_x)
                        x_max = int((xywh[0] + xywh[2] / 2) * shape_x)
                        y_min = int((xywh[1] - xywh[3] / 2) * shape_y)
                        y_max = int((xywh[1] + xywh[3] / 2) * shape_y)

                        temp = dog_image[y_min:y_max, x_min:x_max]
                        data = np.ndarray(shape=(1, 224, 224, 3), dtype=np.float32)
                        temp = cv2.cvtColor(temp, cv2.COLOR_BGR2RGB)
                        if two_dogs:
                            if not already_loaded:
                                dog_name_model = keras.models.load_model('two_dogs.h5')
                                already_loaded = True
                            resized_image_array = cv2.resize(temp, dsize=(224, 224),
                                                                interpolation=cv2.INTER_CUBIC)
                            data[0] = resized_image_array
                            results = dog_name_model.predict(data)
                            print(results)
                            dog_name = two_dog_labels[int(round(results[0][0]))]


                        normalized_image_array = (temp.astype(np.float32) / 127.0) - 1
                        normalized_image_array = cv2.resize(normalized_image_array, dsize=(224, 224),
                                                            interpolation=cv2.INTER_CUBIC)
                        data[0] = normalized_image_array
                        prediction_d = dog_act_detect_model.predict(data)
                        dog_action = dog_actions[np.argmax(prediction_d)]

                        annotator.box_label(xyxy, str(dog_name)+" "+dog_action, color=colors(c, True))
                    if save_crop:
                        save_one_box(xyxy, imc, file=save_dir / 'crops' / names[c] / f'{p.stem}.jpg', BGR=True)

            # Stream results
            im0 = annotator.result()
            cv2.imwrite('t.jpg', im0)
            global response_img
            response_img = (b'--frame\r\n'
                            b'Content-Type: image/jpeg\r\n\r\n' + open('t.jpg', 'rb').read() + b'\r\n')
            # yield (b'--frame\r\n'
            #        b'Content-Type: image/jpeg\r\n\r\n' + open('t.jpg', 'rb').read() + b'\r\n')
            # # Save results (image with detections)
            # if save_img:
            #     if dataset.mode == 'image':
            #         cv2.imwrite(save_path, im0)
        capture_time = time()+(60*60*9)
        if (int(capture_time)-start_stream) % 3== 0 and not captured:
            if previous != dog_action:
                save_path = now_path + "/static/images/"+strftime('%Y-%m-%d',gmtime(capture_time))
                if not os.path.exists(save_path):
                    os.mkdir(save_path)
                sv_path = save_path+"/"+dog_action+str(int(capture_time))[-5:]+".jpg"
                cv2.imwrite(sv_path, dog_image)
                img_db = Image(datetime=strftime('%Y-%m-%d %H:%M:%S',gmtime(capture_time)), pose = dog_action,path = "static/images/"+strftime('%Y-%m-%d',gmtime(capture_time))+"/"+dog_action+str(int(capture_time))[-5:]+".jpg")
                with app.app_context():
                    db.session.add(img_db)
                    db.session.commit()

            previous = dog_action


            # LOGGER.info(f"{s}{'' if len(det) else '(no detections), '}{dt[1].dt * 1E3:.1f}ms"+" dog_action:"+dog_action + " capture_time:"+strftime('%Y-%m-%d %H:%M:%S %p', gmtime(capture_time)))
            captured = True

        else:
            # Print time (inference-only)
            # LOGGER.info(f"{s}{'' if len(det) else '(no detections), '}{dt[1].dt * 1E3:.1f}ms")
            if (int(capture_time)-start_stream) % 3 != 0:
                captured = False
    # # Print results
    # t = tuple(x.t / seen * 1E3 for x in dt)  # speeds per image
    # LOGGER.info(f'Speed: %.1fms pre-process, %.1fms inference, %.1fms NMS per image at shape {(1, 3, *imgsz)}' % t)
    # if save_txt or save_img:
    #     s = f"\n{len(list(save_dir.glob('labels/*.txt')))} labels saved to {save_dir / 'labels'}" if save_txt else ''
    #     LOGGER.info(f"Results saved to {colorstr('bold', save_dir)}{s}")
    # if update:
    #     strip_optimizer(weights[0])  # update model (to fix SourceChangeWarning)


def parse_opt():
    parser = argparse.ArgumentParser()
    parser.add_argument('--weights', nargs='+', type=str, default=ROOT / 'yolov5s.pt', help='model path or triton URL')
    parser.add_argument('--source', type=str, default=ROOT / 'data/images', help='file/dir/URL/glob/screen/0(webcam)')
    parser.add_argument('--data', type=str, default=ROOT / 'data/coco128.yaml', help='(optional) dataset.yaml path')
    parser.add_argument('--imgsz', '--img', '--img-size', nargs='+', type=int, default=[640], help='inference size h,w')
    parser.add_argument('--conf-thres', type=float, default=0.25, help='confidence threshold')
    parser.add_argument('--iou-thres', type=float, default=0.45, help='NMS IoU threshold')
    parser.add_argument('--max-det', type=int, default=1000, help='maximum detections per image')
    parser.add_argument('--device', default='', help='cuda device, i.e. 0 or 0,1,2,3 or cpu')
    parser.add_argument('--view-img', action='store_true', help='show results')
    parser.add_argument('--save-txt', action='store_true', help='save results to *.txt')
    parser.add_argument('--save-conf', action='store_true', help='save confidences in --save-txt labels')
    parser.add_argument('--save-crop', action='store_true', help='save cropped prediction boxes')
    parser.add_argument('--nosave', action='store_true', help='do not save images/videos')
    parser.add_argument('--classes', nargs='+', type=int, help='filter by class: --classes 0, or --classes 0 2 3')
    parser.add_argument('--agnostic-nms', action='store_true', help='class-agnostic NMS')
    parser.add_argument('--augment', action='store_true', help='augmented inference')
    parser.add_argument('--visualize', action='store_true', help='visualize features')
    parser.add_argument('--update', action='store_true', help='update all models')
    parser.add_argument('--project', default=ROOT / 'runs/detect', help='save results to project/name')
    parser.add_argument('--name', default='exp', help='save results to project/name')
    parser.add_argument('--exist-ok', action='store_true', help='existing project/name ok, do not increment')
    parser.add_argument('--line-thickness', default=3, type=int, help='bounding box thickness (pixels)')
    parser.add_argument('--hide-labels', default=False, action='store_true', help='hide labels')
    parser.add_argument('--hide-conf', default=False, action='store_true', help='hide confidences')
    parser.add_argument('--half', action='store_true', help='use FP16 half-precision inference')
    parser.add_argument('--dnn', action='store_true', help='use OpenCV DNN for ONNX inference')
    parser.add_argument('--vid-stride', type=int, default=1, help='video frame-rate stride')
    opt = parser.parse_args()
    opt.imgsz *= 2 if len(opt.imgsz) == 1 else 1  # expand
    print_args(vars(opt))
    return opt


def main(opt):
    check_requirements(exclude=('tensorboard', 'thop'))
    run(**vars(opt))



@app.route('/main')
def index():
    """Video streaming"""
    images = Image.query.order_by(desc(Image.datetime)).limit(10).all()
    return render_template('imagesList.html',imgs = images, morningaction=[False]*5, eveningaction=[False]*5)


@app.route('/detail')
def detail():
    """Video streaming"""
    parameter_dict = request.args.to_dict()
    img_path = parameter_dict["path"]
    pose = parameter_dict["pose"]
    times = parameter_dict["time"]
    return render_template('imageDetail.html', img=img_path, pose=pose, time=times)


@app.route('/delete')
def delete():
    """Video streaming"""
    parameter_dict = request.args.to_dict()
    img_path = parameter_dict["path"]
    db.session.query(Image).filter(Image.path==img_path).\
        delete()
    db.session.commit()

    if os.path.isfile(now_path+"/"+img_path):
        os.remove(now_path+"/"+img_path)

    return redirect("/main")


@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""

    return Response(get_video(),
                mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/renewimg")
def renew(): # you need an endpoint on the server that returns your info...
    images = Image.query.order_by(desc(Image.datetime)).limit(10).all()
    return render_template('renew.html', imgs=images)

@app.route('/login', methods=['POST','GET'])
def login():
    id = request.form['uname']
    pw = request.form['psw']

    if (id == "root" and pw == "1234"):
        session["id"] = id
    return render_template('selectmenu.html')

@app.route('/')
def start():
    return render_template('login.html')


@app.route("/imgList")
def _list():
    page = request.args.get('page', type=int, default=1)  # ?????????
    date = request.args.get('date', type=str, default=strftime('%Y-%m-%d', gmtime(time() + (60 * 60 * 9))))
    pose = request.args.get('pose', type=str, default="ALL")

    if pose == "ALL":
        images = Image.query.filter(Image.datetime.cast(Date) == date).order_by(desc(Image.datetime))
    else:
        images = Image.query.filter((Image.datetime.cast(Date) == date) & (Image.pose == pose)).order_by(desc(Image.datetime))


    if len(images.all()) != 0:
        page_lists = images.paginate(page = page, per_page=20)
        return render_template('lists.html', imgs=page_lists)
    else:
        return "???????????? ????????????."


@app.route("/searchimg", methods = ['GET'])
def searchimg(): # you need an endpoint on the server that returns your info...
    page = request.args.get('page', type=int, default=1)  # ?????????
    date = request.args.get('date', type=str, default=strftime('%Y-%m-%d', gmtime(time() + (60 * 60 * 9))))
    pose = request.args.get('pose', type=str, default="ALL")


    if pose == "ALL":
        images = Image.query.filter(Image.datetime.cast(Date) == date).order_by(desc(Image.datetime))
    else:
        images = Image.query.filter((Image.datetime.cast(Date) == date) & (Image.pose == pose)).order_by(desc(Image.datetime))
    if len(images.all()) != 0:
        page_lists = images.paginate(page = page, per_page=20)
        return render_template('search_renew.html', imgs=page_lists)
    else:
        return "???????????? ????????????."


@app.route("/go_select")
def go_select():
    return render_template('selectmenu.html')

@app.route("/go_one_select")
def go_one_select():
    return render_template('inputonedog.html')

@app.route("/go_two_select")
def go_two_select():
    return render_template('fileUpload.html')

@app.route("/renewtable")
def renewtable():
    date = strftime('%Y-%m-%d', gmtime(time() + (60 * 60 * 9)))
    starts = date+" 00:00:00"
    morning = date+" 12:00:00"
    evening = date+" 23:59:59"
    morning_result = [False]*5
    evening_result = [False] * 5
    actions = ["eating", "sitting", "yawn", "kneeldown","running"]
    loc = 0
    for action in actions:
        image1 = Image.query.filter((starts<=Image.datetime)&(Image.datetime<morning) & (Image.pose == action)).all()
        image2 = Image.query.filter((morning <= Image.datetime) & (Image.datetime<= evening) & (Image.pose == action)).all()
        if image1:
            morning_result[loc] = True
        if image2:
            evening_result[loc] = True
        loc+=1
    return render_template('actionexist.html', morningaction=morning_result, eveningaction=evening_result)

@app.route("/test")
def test():
    return render_template('fileUpload.html')

@app.route("/singledog", methods=["GET","POST"])
def singledog():
    global dog_name
    global two_dogs
    global already_loaded
    if request.method == "POST":
        two_dogs = False
        already_loaded = False
        dog_name = request.form["dogname"]
        print(dog_name)
    return redirect("/main")

@app.route("/upload", methods=["GET","POST"])
def upload():
    if request.method == "POST":
        value = dict(request.form)
        dog1 = value["dog1"]
        dog2 = value["dog2"]
        prevs = glob.glob('static/dogs/*')
        for f in prevs:
            files_in = glob.glob(f.replace("\\","/",10)+"/*")
            for file_in in files_in:
                os.remove(file_in.replace("\\","/",10))
            os.rmdir(f.replace("\\","/",10))
        for seq_file, seq_dog in [["file1",dog1], ["file2",dog2]]:
            files = request.files.getlist(seq_file)
            UPLOAD_FOLDER = 'static/dogs/'+seq_dog
            app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

            os.mkdir(UPLOAD_FOLDER)
            for file in files:
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
        make_keras()
    global two_dogs
    two_dogs = True
    return redirect("/main")


def make_keras():
    global two_dog_labels

    train_datagen = ImageDataGenerator(rescale=1./255,
    width_shift_range = 0.2,
    height_shift_range = 0.2,
    fill_mode='nearest',
    validation_split = 0.2)

    model = Sequential([
        layers.Input(shape=(224, 224, 3)),
        layers.Conv2D(16, 3, padding='same', activation='relu'),
        layers.MaxPooling2D(),
        layers.Conv2D(32, 3, padding='same', activation='relu'),
        layers.MaxPooling2D(),
        layers.Conv2D(64, 3, padding='same', activation='relu'),
        layers.MaxPooling2D(),
        layers.Flatten(),
        layers.Dense(128, activation='relu'),
        layers.Dense(1, activation="sigmoid")
    ])
    train_generator = train_datagen.flow_from_directory(
        'static/dogs',
        batch_size=16,
        target_size=(224, 224),
        class_mode='binary'
    )

    two_dog_labels = [0,0]
    for key,value in train_generator.class_indices.items():
        two_dog_labels[value] = key
    # early_stopping
    early_stopping = EarlyStopping(
        monitor="loss",
        min_delta=0,
        verbose=1,
        patience=5,
        restore_best_weights=True
    )
    model.compile(loss='binary_crossentropy', metrics=['accuracy'], optimizer='adam')
    model.fit(train_generator,batch_size=64, epochs=100,callbacks=[early_stopping])

    model.save("two_dogs.h5")


if __name__ == '__main__':
    opt = parse_opt()
    proc = Thread(target=main, args=(opt,))
    proc.start()
    app.secret_key = os.urandom(24)
    app.run(host='0.0.0.0', port=3000)
