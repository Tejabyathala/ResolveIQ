
import csv
from pathlib import Path

from src.engine.anomaly_detector import detect_all_anomalies


ROOT = Path(__file__).resolve().parents[2]

GROUND_TRUTH = (
    ROOT / "output" / "ground_truth" / "ground_truth.csv"
)


def evaluate_detection():
    detected = detect_all_anomalies()

    with open(GROUND_TRUTH, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        actual = {
            (row["record_id"], row["anomaly_type"])
            for row in reader
        }

    predicted = {
        (item["record_id"], item["anomaly_type"])
        for item in detected
    }

    true_positives = actual & predicted
    false_positives = predicted - actual
    false_negatives = actual - predicted

    precision = (
        len(true_positives) / len(predicted)
        if predicted else 0
    )

    recall = (
        len(true_positives) / len(actual)
        if actual else 0
    )

    f1_score = (
        2 * precision * recall / (precision + recall)
        if precision + recall else 0
    )

    return {
        "total_actual": len(actual),
        "total_predicted": len(predicted),
        "true_positives": len(true_positives),
        "false_positives": len(false_positives),
        "false_negatives": len(false_negatives),
        "precision": precision,
        "recall": recall,
        "f1_score": f1_score,
    }


if __name__ == "__main__":
    results = evaluate_detection()

    for key, value in results.items():
        print(f"{key.upper()}: {value}")
