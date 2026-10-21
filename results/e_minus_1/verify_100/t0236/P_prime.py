a = get_objects_of_category(log_dir, category='VEHICLE')
a = stationary(a, log_dir)
b = get_objects_of_category(log_dir, category='REGULAR_VEHICLE')
b = has_velocity(b, log_dir, min_velocity=2)
b_gate = center_distance_gate(a, b, log_dir, max_center_dist=30)  # implicit 30 m centre-distance neighbour gate, identical in P and P'
out = scenario_and([following(a, b, log_dir), b_gate])