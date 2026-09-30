from services.crop_service import predict_crop, train_and_save_model


def test_training_creates_model_and_metrics(tmp_path):
    dataset = tmp_path / 'Crop_recommendation.csv'
    dataset.write_text(
        'N,P,K,temperature,humidity,ph,rainfall,label\n'
        '90,42,43,20,82,6.5,210,Rice\n'
        '70,52,48,22,68,7,160,Wheat\n'
        '80,50,30,29,63,6,110,Maize\n'
        '20,50,30,23,58,6.9,75,Chickpea\n'
        '45,58,40,26,65,7.2,105,Cotton\n',
        encoding='utf-8',
    )

    metrics = train_and_save_model(
        dataset,
        model_path=tmp_path / 'test_model.pkl',
        metrics_path=tmp_path / 'test_metrics.json',
    )
    assert metrics['best_model'] in {'Decision Tree', 'Random Forest', 'KNN'}
    assert 'best_f1_score' in metrics
    assert metrics['dataset_size'] == 5
    assert metrics['test_samples'] > 0

    result = predict_crop({"N": 90, "P": 42, "K": 43, "temperature": 20, "humidity": 82, "ph": 6.5, "rainfall": 210})
    lowercase_result = predict_crop({"nitrogen": 90, "phosphorus": 42, "potassium": 43, "temperature": 20, "humidity": 82, "ph": 6.5, "rainfall": 210})
    assert isinstance(result['recommended_crop'], str)
    assert lowercase_result == result
    assert result['confidence'] >= 0
    assert result['top_3']
