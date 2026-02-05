# Task Components

This directory contains components related to task management and scheduling.

## ScheduleInput

A comprehensive cron schedule builder component with multiple input modes and real-time validation.

### Features

- **Preset Options**: Quick selection for common schedules (Daily, Weekly, Monthly, Hourly)
- **Visual Builder**: User-friendly dropdown interface for building cron expressions
- **Custom Mode**: Raw cron expression input for advanced users with examples
- **Real-time Validation**: Validates cron expressions as you type
- **Natural Language Preview**: Shows human-readable description using cronstrue
- **Next Executions**: Displays the next 5 scheduled execution times
- **Keyboard Accessible**: Full keyboard navigation support
- **Mobile Responsive**: Works seamlessly on all screen sizes
- **Tooltips**: Helpful hints for each cron field

### Usage

```tsx
import { ScheduleInput } from '@/components/tasks'

function TaskForm() {
  const [schedule, setSchedule] = useState('0 9 * * *')

  return (
    <ScheduleInput
      value={schedule}
      onChange={setSchedule}
      className="w-full"
    />
  )
}
```

### Props

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `value` | `string` | Yes | Current cron expression value |
| `onChange` | `(value: string) => void` | Yes | Callback when the cron expression changes |
| `className` | `string` | No | Additional CSS classes |

### Cron Expression Format

The component works with standard 5-field cron expressions:

```
* * * * *
│ │ │ │ │
│ │ │ │ └─ Day of Week (0-6, Sunday = 0)
│ │ │ └─── Month (1-12)
│ │ └───── Day of Month (1-31)
│ └─────── Hour (0-23)
└───────── Minute (0-59)
```

### Examples

- `0 9 * * *` - Every day at 9:00 AM
- `0 */6 * * *` - Every 6 hours
- `30 14 * * 1-5` - Weekdays at 2:30 PM
- `0 0 1 * *` - First day of every month at midnight
- `0 9 * * 1` - Every Monday at 9:00 AM

### Dependencies

- `cronstrue` - Converts cron expressions to human-readable descriptions
- `cron-parser` - Validates and parses cron expressions

### Accessibility

The component follows WAI-ARIA best practices:

- All form controls have proper labels
- Keyboard navigation is fully supported
- ARIA attributes for invalid states
- Focus management for modal interactions
- Tooltips provide additional context
