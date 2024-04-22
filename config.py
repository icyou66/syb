# 人脸识别模式，该选项为True时会进行人脸识别，若为False则绕过人脸。
face_api = False

# 上报时间间隔，每次上报任务点的时长为30秒，间隔自己把握。若想要1倍速就填30。经测试该间隔对于总时长并无影响。
interval = 1

# 是否开启多线程模式刷课。该选项为True时启动多线程完成任务，若为False则按单线程
thread_api = True

# 多线程数量。该选项必须在thread_api为True时才生效。经测试线程数量为10-15时最稳定。
thread_semaphore = 10
