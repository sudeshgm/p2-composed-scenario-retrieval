a = get_objects_of_category(log_dir, category='REGULAR_VEHICLE')
a = turning(a, log_dir, direction='right')
b = get_objects_of_category(log_dir, category='VEHICLE')
b_gate = center_distance_gate(a, b, log_dir, max_center_dist=30)  # implicit 30 m centre-distance neighbour gate, identical in P and P'
out = scenario_and([heading_toward(a, b, log_dir, max_distance=30), b_gate])