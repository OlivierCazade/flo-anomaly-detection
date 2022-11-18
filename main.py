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

def detect():
    consumer = create_consumer(server="kafka-cluster-kafka-bootstrap.netobserv",
                               topic="netobserv-flows-export",
                               group_id="test")

    model = compose.Pipeline(
        preprocessing.FeatureHasher(),
        preprocessing.MinMaxScaler(),
        anomaly.HalfSpaceTrees(n_trees=8,
                               height=8,
                               window_size=100)
    )
    while True:
        message = consumer.poll(timeout=50)
        if message is None:
            continue
        if message.error():
            logging.error("Consumer error: {}".format(message.error()))
            continue

        # Message that came from producer
        record = json.loads(message.value().decode('utf-8'))
        model = model.learn_one(record)
        score = model.score_one(record)
        if score > 0.8:
            print("======================================")
            print(record)
            print(f'Anomaly score: {score:.3f}')

    consumer.close()


detect()
