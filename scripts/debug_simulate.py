from scripts.validate_moves import simulate_move
from platinum.data.moves import all_moves

moves = all_moves()
slug = 'dragon-rage'
success, info = simulate_move(slug, moves[slug])
print('success', success)
for k in ('damage_dealt','user_hp_changed','stage_changed','status_changed','field_changed','no_effect_msg','nothing_happened_msg','impact_msg'):
    print(k, info.get(k))
print('log:')
print(info.get('log_tail'))
