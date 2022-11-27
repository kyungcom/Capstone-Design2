# Capstone Design2 2022-2
# YOLO를 이용한 반려견 CCTV
* 경희대학교 컴퓨터공학과 박인호

## 개요
### 연구배경

![image](https://user-images.githubusercontent.com/72953874/204126378-34d7b8c2-1b7b-4f85-979d-e8a07c7aee86.png)

반려동물을 키울때 가장 어려운 점은 혼자두고 외출이 어렵다는 점인데 이는 반려견 cctv로 해소시켜줄 수 있으나 기존 제품들을 살펴보면

![image](https://user-images.githubusercontent.com/72953874/204127038-c42fc83d-f830-4860-a2ec-c0c8465602e9.png)

![image](https://user-images.githubusercontent.com/72953874/204127254-d0f074ae-bfc5-4391-8583-fc3c9951bb2c.png)
[펫시몬](https://play.google.com/store/apps/details?id=com.code.trakq.security)

이렇게 추가 하드웨어가 필요하고, 단순한 녹화기능만 존재한다.

이런 단순한 녹화로는 우리의 소중한 반려견이 밥은 먹었는지, 잠은 잘 잤는지 쉽게 확인하기가 어렵다.

### 연구의 중요성/독창성
따라서 해당 연구에서는 단순한 녹화가 아닌 반려견을 탐지하고, 행동을 분류하여 특정 행동을 언제 했는지 탐지하고, 기록하는 기능을 구현하고자 한다.

### 관련연구

1. Yolov5
![image](https://user-images.githubusercontent.com/72953874/204129399-d6973f11-36bc-41eb-b608-5932c09e65e3.png)

Object detection의 1-stage detector로 2-stage detector보다 정확도는 낮지만 FPS가 높아 실시간 cctv를 처리하는 해당 연구에 적합하다. 또한 Yolov5는 pytorch기반으로 작성되어 쉽게 사용할 수 있다.<br>

또한, 다른 yolo 버젼들과 비교하여 용량이적고 속도가 빠르다는 장점을 가지고 있다.

![image](https://user-images.githubusercontent.com/72953874/204129631-19418d3f-66e3-41ba-add1-9a0bfd45d0bf.png)
![image](https://user-images.githubusercontent.com/72953874/204129632-90e835a2-7d0b-41d3-9cbc-eeb2e8c1105d.png)


2. Google Teachable Machine

![image](https://user-images.githubusercontent.com/72953874/204129504-1ae917f4-cce3-4c3f-bbe9-4956a7911e33.png)

쉽게 모델을 학습하고 export하여 사용 할수있는 서비스로, js, keras 등등으로 export 할 수 있어서 편리하다. 본 연구에서는 행동분류를 위한 모델로 사용된다. 본 연구에서는 keras로 export하여 yolov5를 통과한 이미지에 대해서 행동분류를 진행한다.

3. Flask

![image](https://user-images.githubusercontent.com/72953874/204129587-fd5a589a-9f12-4d4e-83a9-fefd9634c102.png)

파이썬 기반의 웹 프레임워크로 해당 연구에서 파이썬 기반으로 작성된 yolov5에 간편하게 덧입혀 쉽게 웹 서버를 구축한다. 또한 jinja 템플릿 엔진을 통해 동적 페이지를 만들어준다.


## Results
1. YOLOV5 학습


2. Teachable Machine 학습

3. 추가기능 

``` python
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
```

4. Flask 웹 서버 구축


5. 결과

## Conclusion
* Summary

* Future plan

## References
