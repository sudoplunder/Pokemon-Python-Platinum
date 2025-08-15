from platinum.encounters.loader import available_methods

def test_method_gating():
    base = available_methods("route201")
    assert "grass" in base and "old_rod" not in [m for m in base if m == 'old_rod']  # since no rod flag
    with_rod = available_methods("route201", has_old_rod=True)
    assert "old_rod" in with_rod
    no_surf = available_methods("route201", has_old_rod=True)
    assert "water" not in no_surf
    with_surf = available_methods("route201", has_old_rod=True, has_surf=True)
    assert "water" in with_surf
