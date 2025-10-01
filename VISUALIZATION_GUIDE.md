# Visualization Guide

## Overview

The WoW Fisher bot includes a comprehensive live visualization system that helps you monitor the bot's performance in real-time.

## Enabling Live View

```bash
python bot.py --live-view
```

## Window Configuration

### Multi-Monitor Setup

By default, the visualization window opens on your **second monitor** (monitor 2). This allows you to:
- Keep WoW on your primary monitor (monitor 1)
- Monitor the bot on your secondary monitor (monitor 2)

Configure in `config.json`:
```json
{
    "viz_window_monitor": 2,      // Which monitor (1, 2, 3, etc.)
    "viz_window_width": 1200,      // Window width in pixels
    "viz_window_height": 800,      // Window height in pixels
    "viz_window_x": null,          // Override X position (null = auto-center)
    "viz_window_y": null,          // Override Y position (null = auto-center)
    "viz_show_fps": true,          // Show FPS counter
    "viz_show_audio_graph": true   // Show audio graph
}
```

### Windowed Mode

The window opens in **WINDOW_NORMAL** mode, which means:
- ✅ Resizable by dragging corners
- ✅ Movable by dragging title bar
- ✅ Does not interfere with WoW window
- ✅ Can be minimized/maximized
- ✅ Stays on designated monitor

## Visual Elements

### 1. Status Panel (Top Left)

```
┌─────────────────────────────────┐
│ WoW Fisher - Live View          │
│ Status: DETECTING_BOBBER        │ ← Color-coded by state
│ Fish Caught: 42                 │
│ FPS: 8.3                        │ ← Performance indicator
│ Cast: 45                        │
│ Time: 23s                       │
│ Confidence: 87.3%               │
└─────────────────────────────────┘
```

**Status Colors:**
- 🟡 **CASTING** - Yellow (casting fishing line)
- 🟠 **DETECTING_BOBBER** - Orange (searching for bobber)
- 🔵 **WAITING_FOR_BITE** - Cyan (bobber found, waiting for splash)
- 🟢 **CATCHING** - Green (fish detected, clicking)
- 🟢 **LOOTING** - Green (collecting loot)
- ⚪ **IDLE** - Gray (between casts)

### 2. Bobber Detection

When the bobber is detected, you'll see:

```
   ┌─────────────────┐
   │ Bobber: 92.5%   │ ← Confidence score on green background
   └─────────────────┘
        ╔═══════════╗
        ║           ║ ← Green bounding box (3px thick)
        ║     ┼     ║ ← Red crosshair (click target)
        ║           ║
        ╚═══════════╝
      128x96px        ← Bounding box dimensions
```

**Elements:**
- **Green Box**: YOLO detection bounding box
- **Red Crosshair**: Exact click position (center of bobber)
- **White Circle**: Click target indicator
- **Confidence**: Detection confidence percentage
- **Dimensions**: Bobber size in pixels

### 3. Audio Graph (Bottom Right)

```
┌─────────────────────────────────────┐
│ Audio: -52.3 dB                     │
│                                     │
│        Threshold: -45dB ←─ Red line │
│  ╱╲  ╱╲                            │
│ ╱  ╲╱  ╲      ╱╲                  │ ← Audio waveform
│          ╲  ╱  ╲                  │
│           ╲╱                       │
└─────────────────────────────────────┘
```

**Features:**
- **Real-time graph**: Shows last 100 audio samples
- **Threshold line**: Red horizontal line at your configured threshold
- **Color coding**:
  - 🟢 Green line: Above threshold (would trigger)
  - ⚪ Gray line: Below threshold (normal)
- **Current level**: Displayed at top of graph

### 4. FPS Counter

Shows visualization frame rate:
- 🟢 **> 5 FPS**: Good (green)
- 🟠 **2-5 FPS**: Moderate (orange)
- 🔴 **< 2 FPS**: Slow (red)

## Performance Tips

### Optimal FPS

The bot performs best at 5-10 FPS. Higher isn't necessarily better since:
- Detection runs every 2 seconds (configurable)
- YOLO inference takes ~200-500ms on CPU
- Screen capture is lightweight

### If FPS is Too Low

1. **Reduce window size**:
   ```json
   "viz_window_width": 800,
   "viz_window_height": 600
   ```

2. **Disable audio graph**:
   ```json
   "viz_show_audio_graph": false
   ```

3. **Use smaller game window**: The bot captures the entire WoW window

## Keyboard Shortcuts

While the visualization window is focused:
- **Ctrl+C**: Stop the bot (in terminal)
- **Window drag**: Move window to different position
- **Corner drag**: Resize window

## Troubleshooting

### Window doesn't appear on second monitor

Check your monitor setup:
```bash
python -c "from screeninfo import get_monitors; [print(f'Monitor {i+1}: {m}') for i, m in enumerate(get_monitors())]"
```

Then adjust in config:
```json
"viz_window_monitor": 1  // Use primary monitor instead
```

### Window appears but is blank

- Ensure WoW window is visible and not minimized
- Check that window name is exactly "World of Warcraft"
- Try `--debug` mode for verbose output

### Audio graph not showing

- Check microphone is working: `arecord -l`
- Ensure PyAudio is installed: `pip install pyaudio`
- Audio detection starts when bobber is found

### Window is too small/large

Adjust size in config:
```json
"viz_window_width": 1600,   // Larger
"viz_window_height": 1200
```

Or manually resize by dragging corners.

## Advanced Configuration

### Custom Position

Override auto-centering:
```json
"viz_window_x": 1920,  // X coordinate
"viz_window_y": 0      // Y coordinate
```

Useful for:
- Triple monitor setups
- Specific screen positions
- Recording/streaming layouts

### Minimal Display

For lower system impact:
```json
"viz_show_fps": false,
"viz_show_audio_graph": false
```

This shows only status and detection info.

## Examples

### Dual Monitor Setup (Recommended)

```json
{
    "viz_window_monitor": 2,
    "viz_window_width": 1200,
    "viz_window_height": 800
}
```

Result: Centered on second monitor, good size for monitoring

### Triple Monitor Setup

```json
{
    "viz_window_monitor": 3,
    "viz_window_width": 1920,
    "viz_window_height": 1080
}
```

Result: Full screen on third monitor

### Single Monitor (Windowed WoW)

```json
{
    "viz_window_monitor": 1,
    "viz_window_width": 800,
    "viz_window_height": 600,
    "viz_window_x": 0,
    "viz_window_y": 0
}
```

Result: Small window in top-left corner

### Recording/Streaming Setup

```json
{
    "viz_window_monitor": 2,
    "viz_window_width": 1920,
    "viz_window_height": 1080,
    "viz_show_fps": true,
    "viz_show_audio_graph": true
}
```

Result: Full HD window with all info for OBS capture
