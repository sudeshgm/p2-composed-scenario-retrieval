a = scenario_or([get_objects_of_category(log_dir, category='BOX_TRUCK'), get_objects_of_category(log_dir, category='TRUCK'), get_objects_of_category(log_dir, category='TRUCK_CAB')])
a = changing_lanes(a, log_dir)
b = get_objects_of_category(log_dir, category='REGULAR_VEHICLE')
b = has_velocity(b, log_dir, min_velocity=2)
b_gate = center_distance_gate(a, b, log_dir, max_center_dist=30)  # implicit 30 m centre-distance neighbour gate, identical in P and P'
out = scenario_and([has_objects_in_relative_direction(a, b, log_dir, direction='left', within_distance=15, lateral_thresh=2.5), b_gate])