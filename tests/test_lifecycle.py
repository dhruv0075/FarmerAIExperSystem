from services.lifecycle_service import get_crop_stage_summary


def test_cycle_summary_returns_stage_and_dates():
    summary = get_crop_stage_summary('Rice', '2024-01-01')
    assert 'crop_name' in summary
    assert 'current_stage' in summary
    assert 'expected_harvest_date' in summary
    assert 'progress' in summary
    assert summary['days_since_sowing'] >= 0
    assert summary['total_days'] > 0
