import math
import edpu.query_window
import edpu.file_utils
import edpu.calc_time_utils


def fail(msg='fail'):
    raise Exception(msg)

def key_sorted_dict_items(dict_):
    return sorted(dict_.items(), key=lambda t: t[0])

def sorted_dict_keys(dict_):
    return sorted(dict_.keys())

def add_int_to_dict(dict_, key, incr):
    if key not in dict_:
        dict_[key] = 0
    dict_[key] += incr
    if dict_[key] == 0:
        del dict_[key]

def sub_int_from_dict(dict_, key, decr):
    add_int_to_dict(dict_, key, -decr)

def dict_to_text(title, dict_):
    str_ = title + ':\n'
    for name, time in key_sorted_dict_items(dict_):
        if time == 0:
            fail()
        str_ += name + ' - ' + edpu.calc_time_utils.duration_string_with_negative(time) + '\n'
    return str_

def next_weekday(weekday):
    return (weekday + 1) % 7

def weekday_to_string(weekday):
    dict_ = {
        0: 'Mon',
        1: 'Tue',
        2: 'Wed',
        3: 'Thu',
        4: 'Fri',
        5: 'Sat',
        6: 'Sun',
    }
    return dict_[weekday]

class ReportBuilder:
    def __init__(self):
        self.checked_in = {}
        self.checked_out = {}

    def checkin(self, label, time):
        if type(label) is not str:
            fail()
        if type(time) is str:
            time = edpu.calc_time_utils.parse_duration(time)

        add_int_to_dict(self.checked_in, label, time)

    def remove(self, label, time):
        if type(label) is not str:
            fail()
        if type(time) is str:
            time = edpu.calc_time_utils.parse_duration(time)

        sub_int_from_dict(self.checked_in, label, time)

    def rename(self, label, new_label):
        if type(label) is not str:
            fail()
        if type(new_label) is not str:
            fail()

        time = self.checked_in[label]
        sub_int_from_dict(self.checked_in, label, time)
        add_int_to_dict(self.checked_in, new_label, time)

    def transfer_time(self, src_label, dst_label, time):
        self.remove(src_label, time)
        self.checkin(dst_label, time)

    def checkout(self, label, time):
        if type(label) is not str:
            fail()
        if type(time) is str:
            time = edpu.calc_time_utils.parse_duration(time)

        sub_int_from_dict(self.checked_in, label, time)
        add_int_to_dict(self.checked_out, label, time)

    def checkout_one(self, label):
        self.checkout(label, self.checked_in[label])

    def checkout_all(self):
        for label, time in key_sorted_dict_items(self.checked_in):
            self.checkout(label, time)

    def pending_time(self):
        result = 0
        for name, time in key_sorted_dict_items(self.checked_in):
            result += time
        return result

    def checked_out_time(self):
        result = 0
        for name, time in key_sorted_dict_items(self.checked_out):
            result += time
        return result

    def total_time(self):
        return self.pending_time() + self.checked_out_time()

    def get_warnings(self):
        return []

    def get_summary(self):
        result = ''

        if len(self.checked_in) > 0:
            result += dict_to_text('Pending tasks', self.checked_in) + '\n'

        if len(self.checked_out) > 0:
            result += dict_to_text('Checked out tasks', self.checked_out) + '\n'

        result += 'Checked out: ' + edpu.calc_time_utils.duration_string_with_negative(self.checked_out_time()) + '\n'
        result += 'Pending time: ' + edpu.calc_time_utils.duration_string_with_negative(self.pending_time()) + '\n'
        result += 'Total time: ' + edpu.calc_time_utils.duration_string_with_negative(self.total_time()) + '\n'

        return result

class ReportBuilder2(ReportBuilder):
    def __init__(self):
        ReportBuilder.__init__(self)
        self.ongoing_action = None
        self.allowed_leaps = 0

    def start(self, label, time):
        if type(time) is str:
            time = edpu.calc_time_utils.parse_time_point(time)
        if self.ongoing_action is not None:
            fail(self.ongoing_action[0] + ' already running, can\'t start ' + label + ' at ' + edpu.calc_time_utils.time_point_string(time))
        self.ongoing_action = (label, time)

    def stop(self, time):
        if type(time) is str:
            time = edpu.calc_time_utils.parse_time_point(time)
        if self.ongoing_action is None:
            fail('Nothing to stop (at ' + edpu.calc_time_utils.time_point_string(time) + ')')

        label = self.ongoing_action[0]
        passed_time = time - self.ongoing_action[1]
        if passed_time < 0:
            if self.allowed_leaps <= 0:
                fail('Not enough dayleaps for period ' + edpu.calc_time_utils.time_point_string(self.ongoing_action[1]) + ' - ' + edpu.calc_time_utils.time_point_string(time))
            self.allowed_leaps -= 1
            passed_time += 24 * 60

        self.checkin(label, passed_time)
        self.ongoing_action = None

    def switch(self, label, time):
        if type(time) is str:
            time = edpu.calc_time_utils.parse_time_point(time)
        self.stop(time)
        self.start(label, time)

    def allow_leap(self):
        self.allowed_leaps += 1

    def remove_ongoing(self, time):
        if type(time) is str:
            time = edpu.calc_time_utils.parse_duration(time)
        if self.ongoing_action is None:
            fail('No ongoing task to get ' + edpu.calc_time_utils.duration_string_with_negative(time) + ' from')

        self.remove(self.ongoing_action[0], time)

    def transfer_time_ongoing(self, dst_label, time):
        if self.ongoing_action is None:
            fail('No ongoing task to get ' + edpu.calc_time_utils.duration_string_with_negative(time) + ' from')

        self.transfer_time(self.ongoing_action[0], dst_label, time)

    def touch(self, time):
        if type(time) is str:
            time = edpu.calc_time_utils.parse_time_point(time)
        if self.ongoing_action is None:
            fail('No ongoing task to touch at ' + edpu.calc_time_utils.time_point_string(time))

        self.switch(self.ongoing_action[0], time)

    def get_warnings(self):
        result = ReportBuilder.get_warnings(self)
        if self.ongoing_action is not None:
            result.append('Active task (since '
                          + edpu.calc_time_utils.time_point_string(self.ongoing_action[1])
                          + '): ' + self.ongoing_action[0])
        if self.allowed_leaps != 0:
            result.append(str(self.allowed_leaps) + ' day leaps are not used')
        return result

class ReportBuilder3(ReportBuilder2):
    def __init__(self):
        ReportBuilder2.__init__(self)
        self.task_stack = []

    def push(self, label, time):
        if type(time) is str:
            time = edpu.calc_time_utils.parse_time_point(time)
        self.task_stack.append(self.ongoing_action[0])
        self.switch(label, time)

    def push_stop(self, time):
        if type(time) is str:
            time = edpu.calc_time_utils.parse_time_point(time)
        self.task_stack.append(self.ongoing_action[0])
        self.stop(time)

    def pop(self, time):
        if type(time) is str:
            time = edpu.calc_time_utils.parse_time_point(time)
        self.switch(self.task_stack.pop(), time)

    def pop_stop(self, time):
        if type(time) is str:
            time = edpu.calc_time_utils.parse_time_point(time)
        self.start(self.task_stack.pop(), time)

    def drop_stack(self):
        self.task_stack = []

    def get_warnings(self):
        result = ReportBuilder2.get_warnings(self)
        if len(self.task_stack) != 0:
            result.append('Task stack is not empty: ' + ', '.join(self.task_stack))
        return result

ACTION_TYPES = [
    'start',
    'stop',
    'switch',
    'push',
    'push-stop',
    'pop',
    'pop-stop',
    'checkin',
    'checkout',
    'checkout-one',
    'checkout-all',
    'dayleap',
    'remove',
    'remove-ongoing',
    'transfer-time',
    'transfer-time-ongoing',
    'touch',
    'rename',
    'drop-stack',
]

class ActionType:
    def __init__(self, action):
        self._id = ACTION_TYPES.index(action)

    def equals(self, other):
        if type(other) is ActionType:
            return self._id == other._id
        else:
            return self.equals(ActionType(other))

    def to_string(self):
        return ACTION_TYPES[self._id]

def apply_action(builder, action):
    type_ = ActionType(action[0])
    if type_.equals('start'):
        builder.start(action[1], action[2])
    elif type_.equals('stop'):
        builder.stop(action[1])
    elif type_.equals('switch'):
        builder.switch(action[1], action[2])
    elif type_.equals('push'):
        builder.push(action[1], action[2])
    elif type_.equals('push-stop'):
        builder.push_stop(action[1])
    elif type_.equals('pop'):
        builder.pop(action[1])
    elif type_.equals('pop-stop'):
        builder.pop_stop(action[1])
    elif type_.equals('checkin'):
        builder.checkin(action[1], action[2])
    elif type_.equals('checkout'):
        builder.checkout(action[1], action[2])
    elif type_.equals('checkout-one'):
        builder.checkout_one(action[1])
    elif type_.equals('checkout-all'):
        builder.checkout_all()
    elif type_.equals('dayleap'):
        builder.allow_leap()
    elif type_.equals('remove'):
        builder.remove(action[1], action[2])
    elif type_.equals('remove-ongoing'):
        builder.remove_ongoing(action[1])
    elif type_.equals('transfer-time'):
        builder.transfer_time(action[1], action[2], action[3])
    elif type_.equals('transfer-time-ongoing'):
        builder.transfer_time_ongoing(action[1], action[2])
    elif type_.equals('touch'):
        builder.touch(action[1])
    elif type_.equals('rename'):
        builder.rename(action[1], action[2])
    elif type_.equals('drop-stack'):
        builder.drop_stack()
    else:
        fail()

def get_left_time(rbs, annotation, day_limit, today,
                    remaining_days_range, goal_times, mock_time):
    result = ''

    if len(goal_times) == 0:
        fail()

    sum_ = 0
    for num, data in key_sorted_dict_items(rbs):
        if num >= day_limit:
            continue
        sum_ += data.total_time()
    sum_ += mock_time

    remaining_times = []
    for goal_time in goal_times:
        remaining_times.append(edpu.calc_time_utils.parse_duration(goal_time) - sum_)

    remaining_times_str = ''
    first = True
    for remaining_time in remaining_times:
        if not first:
            remaining_times_str += ' / '
        remaining_times_str += edpu.calc_time_utils.duration_string_with_negative(remaining_time)
        first = False

    result += annotation + ': ' + remaining_times_str + ' remaining for this month\n'

    if today in rbs:
        worked_today = rbs[today].total_time()
    else:
        worked_today = 0

    for remaining_days in remaining_days_range:
        result += 'Average work time for ' + str(remaining_days) + ' days: '

        first = True
        for remaining_time in remaining_times:
            if not first:
                result += ' / '

            average_day_time = math.ceil(remaining_time / remaining_days)
            result += edpu.calc_time_utils.duration_string_with_negative(average_day_time)

            if worked_today != 0:
                left_today = average_day_time - worked_today
                result += ' (' + edpu.calc_time_utils.duration_string_with_negative(left_today) + ' left)'

            first = False

        result += '\n'

    return result

def get_work_stats(days, today, goal_times, remaining_days_range,
               remaining_days_range_next, today_work_plan, schedule_info):
    result = ''

    rbs = {}
    for day, data in key_sorted_dict_items(days):
        rb = ReportBuilder3()
        for elem in data:
            apply_action(rb, elem)
        rbs[day] = rb

    warnings = []
    for day, data in key_sorted_dict_items(rbs):
        for warning in data.get_warnings():
            warnings.append('Day ' + str(day) + ' warning: ' + warning)

    if len(warnings) > 0:
        for warning in warnings:
            result += warning + '\n'
        result += '\n'

    if today in rbs:
        result += rbs[today].get_summary()
    else:
        result += 'No work today\n'
    result += '\n'

    month_time = 0
    for _, data in key_sorted_dict_items(rbs):
        month_time += data.total_time()
    result += 'Total time for month: ' + edpu.calc_time_utils.duration_string_with_negative(month_time) + ' (' + str(month_time / 60) + ')\n'

    if len(goal_times) > 0 and remaining_days_range is not None:
        result += '\n'
        result += get_left_time(rbs, 'At the ' + str(today) + ' day start',
                        today, today, remaining_days_range, goal_times, 0)

        if remaining_days_range_next is not None:
            result += '\n'
            result += get_left_time(rbs, 'Leaving now', today + 1, today + 1,
                            remaining_days_range_next, goal_times, 0)

            if today_work_plan is not None:
                result += '\n'
                result += get_left_time(rbs, 'Leaving after ' + today_work_plan,
                                today, today + 1, remaining_days_range_next,
                                goal_times, edpu.calc_time_utils.parse_duration(today_work_plan))

    if schedule_info is not None:
        result += '\n'

        schedule_days = schedule_info[0]
        schedule_first_weekday = schedule_info[1]

        if sorted_dict_keys(schedule_days) != list(range(1, len(schedule_days) + 1)):
            fail()

        cur_weekday = schedule_first_weekday
        for day, data in key_sorted_dict_items(schedule_days):
            if day == today:
                result += '> '

            result += 'Day ' + str(day) + ' (' + weekday_to_string(cur_weekday) + '): ' + data[0]

            if day in rbs:
                result += ' -> ' + edpu.calc_time_utils.duration_string_with_negative(rbs[day].total_time())
                over_time = rbs[day].total_time() - edpu.calc_time_utils.parse_duration(schedule_days[day][0])
                result += ' ' + edpu.calc_time_utils.duration_string_with_negative(over_time, True)

            if len(data[1]) > 0:
                result += ' (note: ' + data[1] + ')'

            result += '\n'
            cur_weekday = next_weekday(cur_weekday)

        est_month_time_passed = 0
        real_month_time_passed = 0
        month_time_left = 0

        for day in range(1, len(schedule_days) + 1):
            if (day < today) and (day in rbs):
                real_month_time_passed += rbs[day].total_time()
                est_month_time_passed += edpu.calc_time_utils.parse_duration(schedule_days[day][0])
            else:
                month_time_left += edpu.calc_time_utils.parse_duration(schedule_days[day][0])

        est_month_time_total = est_month_time_passed + month_time_left
        real_month_time_total = real_month_time_passed + month_time_left

        est_month_time_passed_with_today = est_month_time_passed
        real_month_time_passed_with_today = real_month_time_passed
        real_month_time_total_with_today = real_month_time_total

        if today in rbs:
            real_month_time_passed_with_today += rbs[today].total_time()
            est_month_time_passed_with_today += edpu.calc_time_utils.parse_duration(schedule_days[today][0])
            real_month_time_total_with_today += rbs[today].total_time() - edpu.calc_time_utils.parse_duration(schedule_days[today][0])

        month_time_diff = real_month_time_passed - est_month_time_passed
        month_time_diff_with_today = real_month_time_passed_with_today - est_month_time_passed_with_today

        result += 'Estimation month time: '
        result += edpu.calc_time_utils.duration_string(est_month_time_total) + ' -> ' + edpu.calc_time_utils.duration_string_with_negative(real_month_time_total)
        result += ' / ' + edpu.calc_time_utils.duration_string(est_month_time_passed) + ' -> ' + edpu.calc_time_utils.duration_string_with_negative(real_month_time_passed)
        result += ' ' + edpu.calc_time_utils.duration_string_with_negative(month_time_diff, True)
        result += '\n'

        if today in rbs:
            result += 'Estimation month time (with today): '
            result += edpu.calc_time_utils.duration_string(est_month_time_total) + ' -> ' + edpu.calc_time_utils.duration_string_with_negative(real_month_time_total_with_today)
            result += ' / ' + edpu.calc_time_utils.duration_string(est_month_time_passed_with_today) + ' -> ' + edpu.calc_time_utils.duration_string_with_negative(real_month_time_passed_with_today)
            result += ' ' + edpu.calc_time_utils.duration_string_with_negative(month_time_diff_with_today, True)
            result += '\n'

        if est_month_time_passed != 0:
            real_est_ratio = real_month_time_passed / est_month_time_passed
            result += 'Estimation-start ratio: ' + str(real_est_ratio) + '\n'
            result += 'Progressive estimation: ' + edpu.calc_time_utils.duration_string(math.ceil(est_month_time_total * real_est_ratio)) + '\n'

        if today in rbs:
            if est_month_time_passed_with_today != 0:
                real_est_ratio_with_today = real_month_time_passed_with_today / est_month_time_passed_with_today
                result += 'Estimation-start ratio (with today): ' + str(real_est_ratio_with_today) + '\n'
                result += 'Progressive estimation (with today): ' + edpu.calc_time_utils.duration_string(math.ceil(est_month_time_total * real_est_ratio_with_today)) + '\n'

    return result


def work_stats_viewer(data_filename, goal_times, remaining_days_range,
               remaining_days_range_next, today_work_plan, schedule_info):
    def data_provider():
        data = edpu.file_utils.eval_file(data_filename)
        return get_work_stats(data[0], data[1], goal_times, remaining_days_range,
            remaining_days_range_next, today_work_plan, schedule_info)
    edpu.query_window.run_with_exception_wrapper(data_provider, 'Work time stats')


def get_basic_stats(actions):
    result = ''

    rb = ReportBuilder3()
    for action in actions:
        apply_action(rb, action)

    warnings = rb.get_warnings()
    if len(warnings) > 0:
        for warning in warnings:
            result += warning + '\n'
        result += '\n'

    result += rb.get_summary()

    return result

def basic_stats_viewer(data_filename):
    def data_provider():
        data = edpu.file_utils.eval_file(data_filename)
        return get_basic_stats(data[0][data[1]])
    edpu.query_window.run_with_exception_wrapper(data_provider, 'Time stats')