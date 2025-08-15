import json, os
from platinum.data.loader import get_species, find_by_name, possible_evolutions, level_up_learnset, machine_learnset, all_species_ids

# Basic invariants

def test_species_index_nonempty():
    assert len(tuple(all_species_ids())) == 493


def test_find_by_name_case():
    assert find_by_name('TURTWIG')['id'] == 387


def test_no_post_gen4_moves_sample():
    # Pick a few representative species
    for sid in (395, 130, 133):
        sp = get_species(sid)
        for mv in sp['moves']['level_up']:
            # Gen IV pruning ensures absence of obvious later-gen moves
            assert mv['name'] not in { 'scald', 'hurricane', 'moonblast', 'play-rough' }
        for mv in sp['moves']['machines']:
            assert mv not in { 'scald', 'hurricane', 'moonblast', 'play-rough' }


def test_hidden_ability_generation_pruned():
    # Empoleon hidden ability Competitive (Gen VI) should be pruned
    assert get_species(395)['abilities']['hidden'] is None
    # Eevee Anticipation (Gen IV) retained
    assert get_species(133)['abilities']['hidden'] == 'anticipation'


def test_possible_evolutions_level():
    # Piplup at 16 eligible -> Prinplup
    assert 394 in possible_evolutions(393, level=16)
    # At 15 not ready
    assert 394 not in possible_evolutions(393, level=15)


def test_possible_evolutions_item():
    # Eevee with water-stone
    assert 134 in possible_evolutions(133, item='water-stone')


def test_possible_evolutions_friendship_time():
    # Eevee friendship day -> Espeon
    assert 196 in possible_evolutions(133, friendship=220, time_of_day='day')
    assert 197 in possible_evolutions(133, friendship=220, time_of_day='night')


def test_possible_evolutions_location():
    # Eevee moss-rock -> Leafeon
    assert 470 in possible_evolutions(133, location_feature='moss-rock')


def test_machine_subset_reasonable():
    # Ensure machines list not empty and only strings
    sp = get_species(395)
    assert sp['moves']['machines'] and all(isinstance(m,str) for m in sp['moves']['machines'])

