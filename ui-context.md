# UI & UX Context Rules

## 🎨 Styling Guidelines
- **Theme:** Clean, modern dark mode (slate/zinc background with high-contrast accent colors like git checkemerald or indigo).
- **Layout:** Split-screen or clear dashboard layout where inputs/parameters are on one side and algorithm outputs/visualizations are on the other.

## ⏳ Loading & State Management
- **Never let the app look frozen:** Whenever an AI model, optimization algorithm, or heavy calculation runs, display an explicit loading spinner (`lucide-react` loader or skeleton loader) and descriptive status text (e.g., *"Optimizing vehicle routes across 20 locations..."*).
- **Error States:** Gracefully catch UI or API failures with clean toast notifications rather than breaking the screen.
