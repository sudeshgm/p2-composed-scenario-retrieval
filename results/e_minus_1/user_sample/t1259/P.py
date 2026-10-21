a = get_objects_of_category(log_dir, category='EGO_VEHICLE')
a = changing_lanes(a, log_dir)
b = get_objects_of_category(log_dir, category='PEDESTRIAN')
b_gate = center_distance_gate(a, b, log_dir, max_center_dist=30)  # implicit 30 m centre-distance neighbour gate, identical in P and P'
out = scenario_and([has_objects_in_relative_direction(a, b, log_dir, direction='forward', within_distance=25, lateral_thresh=2.5), b_gate])