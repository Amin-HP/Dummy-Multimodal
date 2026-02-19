from py5canvas import *
import random as rnd
import time

# --- State Variables ---
current_probs = {}
target_probs = {}
active_subset = []
current_text = ""
last_action_time = 0
last_text_time = 0
text_messages = []
action_classes = ["Default Class"] # Fallback
k_num = 3
def parameters():
    return {
        'Actions': {
            'Enabled': True,
            'Interval': (10.0, {'min': 0.1, 'max': 20.0}),
            'File': ('nonsense_label.txt', {'type': 'str'}),
            'Reload': False,
            'Smooth': False,
            'Smooth Factor': (0.1, {'min': 0.01, 'max': 1.0})
        },
        'Text': {
            'Enabled': True,
            'Interval': (2.0, {'min': 0.1, 'max': 10.0}),
            'File': ('messages.txt', {'type': 'str'}),
            'Reload': False
        }
    }

def load_messages(filename):
    global text_messages
    try:
        with open(filename, 'r') as f:
            lines = f.readlines()
        text_messages = [line.strip() for line in lines if line.strip()]
        print(f"Loaded {len(text_messages)} messages from {filename}")
    except Exception as e:
        print(f"Error loading messages from {filename}: {e}")
        text_messages = ["Error Loading File"]

def load_classes(filename):
    global action_classes, active_subset
    try:
        with open(filename, 'r') as f:
            lines = f.readlines()
        # Filter empty lines
        loaded = [line.strip() for line in lines if line.strip()]
        if loaded:
            action_classes = loaded
            print(f"Loaded {len(action_classes)} classes from {filename}")
            # Reset active subset
            active_subset = []
        else:
            print(f"Warning: {filename} is empty")
    except Exception as e:
        print(f"Error loading classes from {filename}: {e}")
        action_classes = ["Error Loading Classes"]

def setup():
    create_canvas(600, 400)
    background(30)
    text_size(20)
    fill(255)

    # Initial Load
    load_messages('messages.txt')
    load_classes('nonsense_label.txt')

def draw():
    global last_action_time, last_text_time, current_probs, target_probs, active_subset, current_text

    background(30)

    # --- Check for Parameter Changes ---
    if param_changed('text.file') or param_changed('text.reload'):
        load_messages(params.text.file)
        if params.text.reload:
             print("Text reload triggered")

    if param_changed('actions.file') or param_changed('actions.reload'):
        load_classes(params.actions.file)
        if params.actions.reload:
            print("Classes reload triggered")

    now = time.time()

    # --- Action Generation ---
    if params.actions.enabled and action_classes:
        should_send = False

        # Initialize subset if empty
        if not active_subset:
             subset_size = min(len(action_classes), 10)
             active_subset = rnd.sample(action_classes, subset_size)
             for cls in active_subset:
                 current_probs[cls] = 0.0
                 target_probs[cls] = 0.0

        # Update Targets periodically
        if now - last_action_time > params.actions.interval:
            last_action_time = now

            # Occasionally swap out a class to keep it dynamic
            if len(action_classes) > len(active_subset) and rnd.random() < 0.3:
                # Remove one random class
                to_remove = rnd.choice(active_subset)
                active_subset.remove(to_remove)
                del target_probs[to_remove]
                # Add one new random class not currently in subset
                available = list(set(action_classes) - set(active_subset))
                if available:
                    new_cls = rnd.choice(available)
                    active_subset.append(new_cls)
                    current_probs[new_cls] = 0.0 # Start from 0
                    target_probs[new_cls] = 0.0

            # Generate new target probabilities for active subset
            raw_target = {k: rnd.random() for k in active_subset}
            total = sum(raw_target.values())
            for k, v in raw_target.items():
                target_probs[k] = v / total

            # If smoothing disabled, jump directly
            if not params.actions.smooth:
                current_probs = target_probs.copy()
                should_send = True

        # Smooth Transition (Update every frame)
        if params.actions.smooth:
            factor = params.actions.smooth_factor
            for cls in active_subset:
                # Use .get() to handle newly added classes or removed ones delicately
                curr = current_probs.get(cls, 0.0)
                targ = target_probs.get(cls, 0.0)
                # Lerp
                current_probs[cls] = curr + (targ - curr) * factor
            should_send = True

        # Prepare data for OSC and Visualization
        sorted_probs = sorted(current_probs.items(), key=lambda x: x[1], reverse=True)
        top_k = sorted_probs[:k_num]

        if should_send:
            osc_args = []
            for cls, prob in top_k:
                osc_args.append(cls)
                osc_args.append(float(prob))

            # Send OSC directly via python-osc client
            send_osc("/action", osc_args)
            # Verify printing isn't too spammy? Maybe print only on interval or change?
            if not params.actions.smooth:
                print(f"Sent /action: {osc_args}")


    # --- Text Generation ---
    if params.text.enabled and text_messages:
        if now - last_text_time > params.text.interval:
            last_text_time = now
            current_text = rnd.choice(text_messages)
            send_osc("/text", current_text)
            print(f"Sent /text: {current_text}")

    # --- Visualization ---
    y = 50
    fill(255)
    text("Dummy Data Generator", 20, 30)

    # Draw Probabilities
    # Use the same sorted list as sent
    top_k_vis = sorted_probs[:k_num] if 'sorted_probs' in locals() else []

    for i, (cls, prob) in enumerate(top_k_vis):
        text(f"{cls}: {prob:.2f}", 20, y + 25)

        bar_width = prob * 300
        no_stroke()
        fill(100, 200, 255)
        rect(200, y + 5, bar_width, 20)
        fill(255)

        y += 40

    # Draw Text
    y += 40
    text(f"Last Text: {current_text}", 20, y)

    # Draw Status
    y += 40
    fill(150)
    text(f"Action Interval: {params.actions.interval:.1f}s", 20, y)
    text(f"Text Interval: {params.text.interval:.1f}s", 200, y)
    text(f"Classes Loaded: {len(action_classes)}", 20, y + 25)

run()
