a = scenario_or([get_objects_of_category(log_dir, category='BOX_TRUCK'), get_objects_of_category(log_dir, category='TRUCK'), get_objects_of_category(log_dir, category='TRUCK_CAB')])
a = accelerating(a, log_dir, min_accel=-np.inf, max_accel=-1.0)
b = get_objects_of_category(log_dir, category='REGULAR_VEHICLE')
b = stationary(b, log_dir)
b_gate = center_distance_gate(a, b, log_dir, max_center_dist=30)  # implicit 30 m centre-distance neighbour gate, identical in P and P'
out = scenario_and([heading_toward(a, b, log_dir, max_distance=30), b_gate])