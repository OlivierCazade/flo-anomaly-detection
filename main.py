import json
import os

from confluent_kafka import Producer, Consumer
import logging
import socket
from river import anomaly, compose, preprocessing

def create_consumer(server, topic, group_id):
    try:
        consumer = Consumer({"bootstrap.servers": server,
                             "group.id": group_id,
                             "client.id": socket.gethostname(),
                             "isolation.level": "read_committed",
                             "default.topic.config": {"auto.offset.reset": "latest", # Only consume new messages
                                                      "enable.auto.commit": True}
                             })

        consumer.subscribe([topic])
    except Exception as e:
        logging.exception("Couldn't create the consumer")
        consumer = None

    return consumer

models = {}

def checkRecordForPod(pod, record):
    #Memory leak here since we never address old models
    model = models.get(pod, compose.Pipeline(
            preprocessing.FeatureHasher(),
            preprocessing.MinMaxScaler(),
            anomaly.HalfSpaceTrees(n_trees=10,
                                   height=10,
                                   window_size=250)
        )
)

    model = model.learn_one(record)
    score = model.score_one(record)
    if score > 0.8:
        print("======================================")
        print(record)
        print(f'Pod: {pod} Anomaly score: {score:.3f}')
    models[pod] = model

def detect():
    consumer = create_consumer(server="kafka-cluster-kafka-bootstrap.netobserv",
                               topic="netobserv-flows-export",
                               group_id="test")
    while True:
        message = consumer.poll(timeout=50)
        if message is None:
            continue
        if message.error():
            logging.error("Consumer error: {}".format(message.error()))
            continue
        record = json.loads(message.value().decode('utf-8'))
        if "Duplicate" in record and record["Duplicate"] is True :
            continue
        if "SrcK8S_Name" in record:
            if "SrcK8S_OwnerType" in record and record["SrcK8S_Type"] == "Pod":
                checkRecordForPod(record["SrcK8S_Name"], record)
        if "DstK8S_Name" in record:
            if "DstK8S_OwnerType" in record and record["DstK8S_Type"] == "Pod":
                checkRecordForPod(record["DstK8S_Name"], record)

    consumer.close()


detect()
