from model_lab.display_schema import DisplaySafetyBanner


def test_display_safety_banner_defaults_are_shadow_only():
    safety = DisplaySafetyBanner()

    assert safety.mode == "shadow_display_only"
    assert safety.is_trading_advice is False
    assert safety.allow_order_execution is False
    assert safety.allow_writeback_to_left_project is False
