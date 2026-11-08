# EKF-Based State Estimation for Indoor UAV

<!--
작성 규칙
- 이 파일에는 발표에서 말할 내용을 직접 쓴다. 클로드에게 시키는 지시문을 쓰지 않는다
  - 쓸 것: "IMU 단독 적분은 바이어스가 누적되어 수십 초 안에 발산한다"
  - 쓰지 말 것: "IMU의 한계를 한 문장으로 적는다"
- 장(##) 은 발표의 묶음이다. 슬라이드 키커로 쓰이므로 영어로 적는다
- 절(###) 은 슬라이드 하나다. 제목도 영어로 적는다
- 불릿 하나는 문단 하나를 압축한 한 문장이다. 구어체를 쓰지 않고 개조식으로 적는다

자료 표기
- 그림   `그림: materials/파일명.png - English alt label`
- 동영상 `동영상: materials/파일명.mp4 - poster: materials/파일명_poster.jpg`
- 표     `표:` 다음 줄부터 마크다운 표를 그대로 적는다. 머리행은 영어로 적는다
- 수식   `수식:` 다음 줄부터 `$$` 로 감싸 적고, 기호 설명을 불릿으로 잇는다
         수식 안에는 ASCII 만 넣는다. 한글, `·`, `×`, `→`, `≤` 를 넣지 않는다
         부등호와 화살표는 명령어로 적는다. `\le` `\ge` `\ne` `\to` `\times` `\in`
         `\*` 는 에러다. `T^{*}` 또는 `T^{\star}` 로 적는다
- 원본 파일은 `materials/` 에 둔다. 덱에 들어가는 변환본은 클로드가 `build/imgs/` 에 만든다

기타
- 장 바로 아래 `구분 슬라이드: 필요` 를 적으면 그 장 앞에 번호 없는 파트 구분 슬라이드가 들어간다
- 다 채웠으면 클로드에 "컨텐츠 제작" 을 지시한다. slide.md 와 review.md 가 만들어진다
- 아래 내용은 표기법을 보여 주는 예시다. 자기 발표 내용으로 바꿔 쓴다
- 이 주석 블록은 지워도 된다
-->

## Cover

- 구분: Lab Seminar
- 파트: Indoor Autonomous Flight
- 주제: EKF-Based State Estimation for Indoor UAV
- 발표: 충북대학교 지능로봇공학과 홍길동

## Introduction

구분 슬라이드: 필요

### Motivation

- 실내 비행 로봇은 GNSS 신호가 차단되어 외부 위치 기준 없이 자기 위치를 추정해야 한다
- IMU 단독 적분은 가속도계 바이어스가 시간의 제곱으로 누적되어 수십 초 안에 발산한다
- LiDAR 스캔 매칭은 드리프트가 작으나 갱신 주기가 10 Hz 수준으로 자세 제어 주기를 만족하지 못한다

그림: materials/sensor_limits.png - IMU drift versus LiDAR update rate

### Problem Statement

- 서로 다른 주기와 오차 특성을 갖는 두 센서를 하나의 상태 추정기로 융합하는 문제를 다룬다
- 난점은 IMU 의 고주파 갱신과 LiDAR 의 저주파 갱신 사이의 시간 정합이다
- 상보 필터는 이득이 고정되어 센서 신뢰도가 구간마다 달라지는 상황을 반영하지 못한다

표:

| Method | Update Rate | Drift | Limitation |
|---|---|---|---|
| IMU integration | 200 Hz | 시간의 제곱으로 누적 | 수십 초 안에 발산 |
| LiDAR scan matching | 10 Hz | 작음 | 제어 주기 미달, 특징 부족 구간에서 실패 |
| Complementary filter | 200 Hz | 중간 | 고정 이득으로 신뢰도 변화 미반영 |

## Proposed Method

구분 슬라이드: 필요

### Filter Formulation

- 상태 벡터를 위치, 속도, 자세, 가속도계 바이어스로 구성한다
- IMU 측정을 예측 단계에, LiDAR 위치 해를 갱신 단계에 배치하여 서로 다른 주기를 처리한다
- 측정 잡음 공분산을 스캔 매칭 잔차로부터 매 갱신마다 산출하여 센서 신뢰도를 반영한다

수식:

$$
\hat{x}_{k} = \hat{x}_{k}^{-} + K_{k}\left(z_{k} - H\hat{x}_{k}^{-}\right), \qquad
K_{k} = P_{k}^{-}H^{\top}\left(H P_{k}^{-} H^{\top} + R_{k}\right)^{-1}
$$

- `x_hat_k` 갱신된 상태 추정값
- `x_hat_k_minus` 예측 단계의 사전 추정값
- `K_k` 칼만 이득
- `z_k` LiDAR 위치 측정값
- `H` 측정 행렬
- `P_k_minus` 사전 오차 공분산
- `R_k` 스캔 매칭 잔차로부터 산출한 측정 잡음 공분산

### System Architecture

- IMU 드라이버, 스캔 매칭, 필터, 제어기를 각각 ROS2 노드로 분리하고 토픽으로 연결한다
- 필터 노드는 IMU 200 Hz 와 LiDAR 10 Hz 를 구독하여 상태 추정값을 100 Hz 로 발행한다

그림: materials/architecture.png - Node graph from sensors to controller

## Experiments

구분 슬라이드: 필요

### Setup and Results

- 실내 12 x 8 m 공간에서 모션캡처 기준값과 대조하여 5회 반복 비행으로 평가한다
- 위치 RMSE 가 상보 필터의 0.42 m 에서 0.11 m 로 74% 감소한다
- 상태 추정 발행 주기는 100 Hz 를 유지하여 자세 제어 루프의 요구 주기를 만족한다

표:

| Metric | Complementary Filter | Proposed |
|---|---|---|
| Position RMSE | 0.42 m | 0.11 m |
| Max error | 0.98 m | 0.27 m |
| Output rate | 200 Hz | 100 Hz |

그림: materials/rmse_plot.png - Position error over time for both filters

### Flight Demonstration

- 실비행 로그를 재생하여 추정 궤적과 모션캡처 기준 궤적을 겹쳐 확인한다
- 스캔 매칭이 실패하는 구간에서 추정값이 예측 단계만으로 유지되는 동작을 확인한다

동영상: materials/flight.mp4 - poster: materials/flight_poster.jpg

## Conclusion

구분 슬라이드: 필요

### Conclusion and Future Works

- IMU 와 LiDAR 를 확장 칼만 필터로 융합하여 GNSS 없이 100 Hz 상태 추정을 달성한다
- 위치 RMSE 0.11 m 로 상보 필터 대비 74% 감소한다
- 스캔 매칭이 실패하는 특징 부족 구간에서 갱신이 중단되는 한계가 남는다
- 시각 센서를 추가하여 특징 부족 구간을 보완하는 작업을 다음 단계로 둔다
