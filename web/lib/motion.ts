/**
 * AttackSurface Timeline — Motion Design System & Interaction Tokens
 * Centralized physics, spring curves, durations, and micro-interaction definitions.
 */

export const MOTION_DURATIONS = {
  instant: 0,
  micro: 140,     // Hover, focus, click feedback
  quick: 200,     // Badges, toggles, small indicator shifts
  normal: 280,    // Dropdowns, drawers, cards, tabs
  spatial: 420,   // Spatial reorientation, node focus, layout transitions
  hero: 700,      // Company open transition, atmospheric shifts
  deliberate: 950 // Temporal replay steps, forensic timeline scrubbing
} as const;

export const MOTION_EASINGS = {
  // Apple/Linear inspired cubic beziers
  snappy: "cubic-bezier(0.2, 0.9, 0.3, 1)",
  glide: "cubic-bezier(0.16, 1, 0.3, 1)",
  spatial: "cubic-bezier(0.22, 1, 0.36, 1)",
  bounce: "cubic-bezier(0.34, 1.56, 0.64, 1)",
  decelerate: "cubic-bezier(0, 0, 0.2, 1)",
  accelerate: "cubic-bezier(0.4, 0, 1, 1)",
  softSpring: "cubic-bezier(0.175, 0.885, 0.32, 1.275)"
} as const;

/**
 * 50+ Distinct Micro-Interaction Pattern Keys
 */
export type MicroInteractionType =
  | "sidebar_expand"
  | "sidebar_collapse"
  | "navigation_morph"
  | "active_indicator_glide"
  | "hover_lift"
  | "magnetic_button"
  | "cursor_spotlight"
  | "card_tilt"
  | "card_depth"
  | "modal_entrance"
  | "modal_exit"
  | "drawer_slide"
  | "drawer_depth"
  | "tooltip_reveal"
  | "command_palette_entrance"
  | "search_result_stagger"
  | "notification_entrance"
  | "notification_stack"
  | "notification_dismiss"
  | "notification_priority_pulse"
  | "number_count_up"
  | "number_count_down"
  | "live_digit_transition"
  | "progress_morph"
  | "skeleton_shimmer"
  | "loading_orbital_motion"
  | "data_refresh_pulse"
  | "new_data_particle_arrival"
  | "removed_data_fade"
  | "timeline_event_reveal"
  | "timeline_scrub"
  | "timeline_replay"
  | "company_focus_transition"
  | "entity_focus_transition"
  | "graph_camera_movement"
  | "node_hover_illumination"
  | "node_selection_expansion"
  | "relationship_highlighting"
  | "evidence_reveal"
  | "source_expansion"
  | "confidence_indicator_animation"
  | "severity_pulse"
  | "alert_escalation"
  | "drag_lift"
  | "drag_preview"
  | "drop_zone_activation"
  | "drop_confirmation"
  | "tab_morph"
  | "segmented_control_slide"
  | "toggle_physics"
  | "toggle_glow"
  | "filter_chip_animation"
  | "filter_removal"
  | "toast_morph"
  | "profile_transition"
  | "settings_panel_transition"
  | "page_transition"
  | "background_environment_transition"
  | "camera_3d_transition"
  | "temporal_rewind"
  | "temporal_forward"
  | "hover_preview"
  | "command_shortcut_animation"
  | "keyboard_focus_animation"
  | "success_confirmation"
  | "error_shake"
  | "warning_pulse"
  | "empty_state_reveal"
  | "expandable_table_row"
  | "live_status_heartbeat";

export const INTERACTION_PRESETS: Record<MicroInteractionType, { durationMs: number; easing: string; description: string }> = {
  sidebar_expand: { durationMs: 280, easing: MOTION_EASINGS.spatial, description: "Smooth spring expansion of command surface" },
  sidebar_collapse: { durationMs: 240, easing: MOTION_EASINGS.glide, description: "Compact collapse with label fade" },
  navigation_morph: { durationMs: 220, easing: MOTION_EASINGS.snappy, description: "Shared layout navigation pill morph" },
  active_indicator_glide: { durationMs: 260, easing: MOTION_EASINGS.glide, description: "Indicator glides along active rail" },
  hover_lift: { durationMs: 160, easing: MOTION_EASINGS.snappy, description: "Subtle 2-4px elevation with specular shadow" },
  magnetic_button: { durationMs: 180, easing: MOTION_EASINGS.bounce, description: "Pulls toward pointer with spring return" },
  cursor_spotlight: { durationMs: 140, easing: MOTION_EASINGS.glide, description: "Radial light field follows pointer position" },
  card_tilt: { durationMs: 180, easing: MOTION_EASINGS.snappy, description: "3D tilt based on pointer offset" },
  card_depth: { durationMs: 240, easing: MOTION_EASINGS.glide, description: "Z-axis translation on selection" },
  modal_entrance: { durationMs: 320, easing: MOTION_EASINGS.spatial, description: "Expands from origin with backdrop blur" },
  modal_exit: { durationMs: 220, easing: MOTION_EASINGS.accelerate, description: "Smooth scale and fade exit" },
  drawer_slide: { durationMs: 300, easing: MOTION_EASINGS.glide, description: "Right-hand operational drawer ingress" },
  drawer_depth: { durationMs: 340, easing: MOTION_EASINGS.spatial, description: "Background surface recedes into depth" },
  tooltip_reveal: { durationMs: 140, easing: MOTION_EASINGS.snappy, description: "Instant precision tooltip emergence" },
  command_palette_entrance: { durationMs: 260, easing: MOTION_EASINGS.spatial, description: "Spotlight command surface drop-down" },
  search_result_stagger: { durationMs: 180, easing: MOTION_EASINGS.glide, description: "Staggered cascaded entry of search hits" },
  notification_entrance: { durationMs: 280, easing: MOTION_EASINGS.bounce, description: "Event arrives and stacks from perimeter" },
  notification_stack: { durationMs: 220, easing: MOTION_EASINGS.glide, description: "Existing cards slide downward smoothly" },
  notification_dismiss: { durationMs: 200, easing: MOTION_EASINGS.accelerate, description: "Swipes out with opacity falloff" },
  notification_priority_pulse: { durationMs: 1200, easing: "ease-in-out", description: "Rhythmic breathing of unacknowledged alerts" },
  number_count_up: { durationMs: 650, easing: MOTION_EASINGS.glide, description: "Spring number interpolation from 0 or previous" },
  number_count_down: { durationMs: 600, easing: MOTION_EASINGS.glide, description: "Interpolation downward for resolved counts" },
  live_digit_transition: { durationMs: 260, easing: MOTION_EASINGS.snappy, description: "Digital clock individual digit slide" },
  progress_morph: { durationMs: 350, easing: MOTION_EASINGS.spatial, description: "Fluid bar length and glow readjustment" },
  skeleton_shimmer: { durationMs: 1600, easing: "linear", description: "Soft graphite scanline reflection across loading cards" },
  loading_orbital_motion: { durationMs: 2400, easing: "linear", description: "Orbital electron ring tracking system state" },
  data_refresh_pulse: { durationMs: 400, easing: MOTION_EASINGS.snappy, description: "HUD border illuminates on telemetry sync" },
  new_data_particle_arrival: { durationMs: 800, easing: MOTION_EASINGS.spatial, description: "Particle enters, arcs, and embeds in layer" },
  removed_data_fade: { durationMs: 300, easing: MOTION_EASINGS.accelerate, description: "Decommissioned asset collapses and fades" },
  timeline_event_reveal: { durationMs: 280, easing: MOTION_EASINGS.snappy, description: "Chronological milestone emerges on rail" },
  timeline_scrub: { durationMs: 200, easing: MOTION_EASINGS.glide, description: "Temporal cursor moves responsively to scrubber" },
  timeline_replay: { durationMs: 850, easing: MOTION_EASINGS.spatial, description: "Step-by-step playback with historical shockwave" },
  company_focus_transition: { durationMs: 650, easing: MOTION_EASINGS.spatial, description: "Origin expansion into company intelligence realm" },
  entity_focus_transition: { durationMs: 450, easing: MOTION_EASINGS.spatial, description: "Reorganizes composition around clicked node" },
  graph_camera_movement: { durationMs: 500, easing: MOTION_EASINGS.glide, description: "Smooth camera dolly and pan to target coordinate" },
  node_hover_illumination: { durationMs: 160, easing: MOTION_EASINGS.snappy, description: "Node halo expands and adjacent paths brighten" },
  node_selection_expansion: { durationMs: 320, easing: MOTION_EASINGS.bounce, description: "Node radius grows with inspectable parameter ring" },
  relationship_highlighting: { durationMs: 240, easing: MOTION_EASINGS.glide, description: "Connected graph edges pulse with electric cyan" },
  evidence_reveal: { durationMs: 300, easing: MOTION_EASINGS.spatial, description: "Forensic chain accordion expands seamlessly" },
  source_expansion: { durationMs: 220, easing: MOTION_EASINGS.snappy, description: "Authoritative provenance card reveals metadata" },
  confidence_indicator_animation: { durationMs: 500, easing: MOTION_EASINGS.glide, description: "Dial or bar fills to exact confidence percentage" },
  severity_pulse: { durationMs: 1500, easing: "ease-in-out", description: "Critical red breathing glow for confirmed CVEs" },
  alert_escalation: { durationMs: 400, easing: MOTION_EASINGS.bounce, description: "Border shifts from amber to crimson" },
  drag_lift: { durationMs: 160, easing: MOTION_EASINGS.snappy, description: "Card rises in Z space with elevated drop shadow" },
  drag_preview: { durationMs: 120, easing: "linear", description: "Physical inertia as card follows pointer" },
  drop_zone_activation: { durationMs: 200, easing: MOTION_EASINGS.snappy, description: "Drop zone border illuminates with magnetic glow" },
  drop_confirmation: { durationMs: 340, easing: MOTION_EASINGS.bounce, description: "Spring settle with subtle success ripple" },
  tab_morph: { durationMs: 220, easing: MOTION_EASINGS.glide, description: "Underline or background pill slides to new active tab" },
  segmented_control_slide: { durationMs: 200, easing: MOTION_EASINGS.glide, description: "Physical sliding switch with tactile feel" },
  toggle_physics: { durationMs: 180, easing: MOTION_EASINGS.bounce, description: "Switch knob springs past threshold then snaps" },
  toggle_glow: { durationMs: 220, easing: MOTION_EASINGS.snappy, description: "Electric cyan halo engages upon activation" },
  filter_chip_animation: { durationMs: 180, easing: MOTION_EASINGS.snappy, description: "Filter tag scales in with dismiss cross" },
  filter_removal: { durationMs: 160, easing: MOTION_EASINGS.accelerate, description: "Chip collapses horizontally and disappears" },
  toast_morph: { durationMs: 260, easing: MOTION_EASINGS.bounce, description: "Compact pill transforms into detailed message" },
  profile_transition: { durationMs: 550, easing: MOTION_EASINGS.spatial, description: "Avatar expands into personal intelligence world" },
  settings_panel_transition: { durationMs: 320, easing: MOTION_EASINGS.spatial, description: "Configuration panel slides with depth shift" },
  page_transition: { durationMs: 400, easing: MOTION_EASINGS.spatial, description: "Spatial environment morphs between route contexts" },
  background_environment_transition: { durationMs: 700, easing: MOTION_EASINGS.glide, description: "Ambient particle color and density morphing" },
  camera_3d_transition: { durationMs: 600, easing: MOTION_EASINGS.spatial, description: "Perspective angle adjusts to active workspace" },
  temporal_rewind: { durationMs: 350, easing: MOTION_EASINGS.glide, description: "Fast reverse animation of historical milestones" },
  temporal_forward: { durationMs: 350, easing: MOTION_EASINGS.glide, description: "Fast forward animation of historical milestones" },
  hover_preview: { durationMs: 180, easing: MOTION_EASINGS.snappy, description: "Instant micro-graph floating preview" },
  command_shortcut_animation: { durationMs: 140, easing: MOTION_EASINGS.snappy, description: "Keyboard pill depresses visually on keydown" },
  keyboard_focus_animation: { durationMs: 160, easing: MOTION_EASINGS.snappy, description: "High-contrast cyan focus ring with pulse" },
  success_confirmation: { durationMs: 400, easing: MOTION_EASINGS.bounce, description: "Verified green checkmark with shockwave" },
  error_shake: { durationMs: 360, easing: MOTION_EASINGS.bounce, description: "Horizontal tactile rejection vibration" },
  warning_pulse: { durationMs: 1000, easing: "ease-in-out", description: "Amber caution glow on unverified evidence" },
  empty_state_reveal: { durationMs: 300, easing: MOTION_EASINGS.spatial, description: "Graceful emergence of empty state illustration" },
  expandable_table_row: { durationMs: 240, easing: MOTION_EASINGS.glide, description: "Row unfolds forensic detail panel" },
  live_status_heartbeat: { durationMs: 2000, easing: "ease-in-out", description: "2-second cyclical telemetry pulse dot" }
};
