import csv
import io
import re
from dataclasses import dataclass
from datetime import date, timedelta


CSV_HEADER = [
    "Subject",
    "Start date",
    "Start time",
    "End date",
    "End time",
    "Description",
    "Location",
]
WEEKDAY_INDEX = {
    "M": 0,
    "T": 1,
    "W": 2,
    "R": 3,
    "F": 4,
    "Sat": 5,
    "Sun": 6,
}


@dataclass(frozen=True)
class MeetingRecord:
    meeting_type: str
    location: str
    weekdays: tuple[str, ...]
    start_time: str | None
    end_time: str | None

    @property
    def is_schedulable(self) -> bool:
        return bool(self.weekdays and self.start_time and self.end_time)


@dataclass(frozen=True)
class CourseRecord:
    course_id: str
    subject_code: str
    course_number: str
    section_number: str
    title: str
    description: str
    meetings: tuple[MeetingRecord, ...]
    final_exam: "FinalExamRecord | None"


@dataclass(frozen=True)
class FinalExamRecord:
    exam_date: date
    start_time: str
    end_time: str
    location: str


@dataclass(frozen=True)
class CsvRow:
    subject: str
    start_date: str
    start_time: str
    end_date: str
    end_time: str
    description: str
    location: str

    def as_list(self) -> list[str]:
        return [
            self.subject,
            self.start_date,
            self.start_time,
            self.end_date,
            self.end_time,
            self.description,
            self.location,
        ]


@dataclass(frozen=True)
class ConversionResult:
    rows: tuple[CsvRow, ...]
    skipped_messages: tuple[str, ...]

    def to_csv_bytes(self) -> bytes:
        return rows_to_csv_bytes(list(self.rows))


def load_html_from_text(html_text: str) -> str:
    return html_text


def load_html_from_bytes(html_bytes: bytes) -> str:
    return html_bytes.decode("utf-8")


def parse_selected_course_ids(html_text: str) -> list[str]:
    return re.findall(r"SelectedList\.(t[0-9A-Z_]+)\s*=", html_text)


def parse_course_record(html_text: str, course_id: str) -> CourseRecord:
    course_object = extract_course_object(html_text, course_id)
    subject_code = extract_string_field(course_object, "SUBJECT_CODE")
    course_number = extract_string_field(course_object, "COURSE_NUMBER")
    section_number = extract_string_field(course_object, "SECTION_NUMBER")
    title = extract_string_field(course_object, "TITLE")
    description = extract_string_field(course_object, "DESCRIPTION")
    meetings = parse_meetings(course_object)
    final_exam = parse_final_exam(course_object)
    return CourseRecord(
        course_id=course_id,
        subject_code=subject_code,
        course_number=course_number,
        section_number=section_number,
        title=title,
        description=description,
        meetings=tuple(meetings),
        final_exam=final_exam,
    )


def extract_course_object(html_text: str, course_id: str) -> str:
    pattern = re.compile(
        rf'CourseDetails\.{re.escape(course_id)}\s*=\s*(\{{.*?\}});',
        re.DOTALL,
    )
    match = pattern.search(html_text)
    if not match:
        raise ValueError(f"Could not find course details for {course_id}.")
    return match.group(1)


def extract_string_field(object_text: str, field_name: str) -> str:
    match = re.search(rf'"{field_name}":"(.*?)"', object_text, re.DOTALL)
    if not match:
        raise ValueError(f"Missing field {field_name}.")
    return decode_js_string(match.group(1)).strip()


def parse_meetings(course_object: str) -> list[MeetingRecord]:
    meetings_match = re.search(
        r'"MEETINGS":\[(.*?)\]\s*,\s*"REGISTRATION_STATUS"',
        course_object,
        re.DOTALL,
    )
    if not meetings_match:
        return []

    meetings_block = meetings_match.group(1)
    meeting_records: list[MeetingRecord] = []
    for meeting_text in re.findall(r"\{(.*?)\}", meetings_block, re.DOTALL):
        meeting_type = extract_optional_string_field(meeting_text, "TYPE") or ""
        location = extract_optional_string_field(meeting_text, "LOCATION") or ""
        weekdays_text = extract_optional_string_field(meeting_text, "WEEKDAYS") or ""
        weekday_tokens = tuple(
            token.strip() for token in weekdays_text.split(",") if token.strip()
        )
        start_time = parse_time_field(meeting_text, "STARTTIME")
        end_time = parse_time_field(meeting_text, "ENDTIME")
        meeting_records.append(
            MeetingRecord(
                meeting_type=meeting_type,
                location=location,
                weekdays=weekday_tokens,
                start_time=start_time,
                end_time=end_time,
            )
        )

    return meeting_records


def extract_optional_string_field(object_text: str, field_name: str) -> str | None:
    match = re.search(rf'"{field_name}":"(.*?)"', object_text, re.DOTALL)
    if not match:
        return None
    return decode_js_string(match.group(1)).strip()


def parse_time_field(object_text: str, field_name: str) -> str | None:
    if re.search(rf'"{field_name}":null', object_text):
        return None

    match = re.search(
        rf'"{field_name}":new Date\(\d+,\s*\d+\s*-\s*1,\s*\d+,\s*(\d+),\s*(\d+)',
        object_text,
    )
    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2))
    return format_24_hour_time(hour, minute)


def format_24_hour_time(hour: int, minute: int) -> str:
    return f"{hour:02d}:{minute:02d}"


def add_hours_to_time(hour: int, minute: int, hours_to_add: int) -> str:
    total_minutes = hour * 60 + minute + (hours_to_add * 60)
    end_hour = (total_minutes // 60) % 24
    end_minute = total_minutes % 60
    return format_24_hour_time(end_hour, end_minute)


def parse_final_exam(course_object: str) -> FinalExamRecord | None:
    match = re.search(
        r'"FINAL_EXAM_STARTDATE":(new Date\((\d+),(\d+),(\d+),(\d+),(\d+),(\d+)\)|null)',
        course_object,
    )
    if not match or match.group(1) == "null":
        return None

    exam_date = date(
        int(match.group(2)),
        int(match.group(3)) + 1,
        int(match.group(4)),
    )
    start_hour = int(match.group(5))
    start_minute = int(match.group(6))
    start_time = format_24_hour_time(start_hour, start_minute)
    end_time = add_hours_to_time(start_hour, start_minute, 2)
    location = ""

    return FinalExamRecord(
        exam_date=exam_date,
        start_time=start_time,
        end_time=end_time,
        location=location,
    )


def decode_js_string(value: str) -> str:
    return (
        value.replace(r"\/", "/")
        .replace(r"\'", "'")
        .replace(r"\"", '"')
        .replace(r"\n", " ")
        .replace(r"\r", " ")
        .replace(r"\t", " ")
    )


def build_csv_rows(
    courses: list[CourseRecord],
    start_date: date,
    end_date: date,
    include_final_exams: bool = False,
) -> tuple[list[CsvRow], list[str]]:
    csv_rows: list[CsvRow] = []
    skipped_messages: list[str] = []

    for course in courses:
        schedulable_found = False
        for meeting in course.meetings:
            if not meeting.is_schedulable:
                skipped_messages.append(
                    f"Skipped {course.title} ({meeting.meeting_type or 'Unknown'}): "
                    "missing weekdays or start/end times."
                )
                continue

            schedulable_found = True
            subject = (
                f"{course.subject_code} {course.course_number} "
                f"{course.section_number} ({meeting.meeting_type})"
            )
            for meeting_date in expand_weekdays(meeting.weekdays, start_date, end_date):
                csv_rows.append(
                    CsvRow(
                        subject=subject,
                        start_date=meeting_date,
                        start_time=meeting.start_time or "",
                        end_date=meeting_date,
                        end_time=meeting.end_time or "",
                        description=course.title,
                        location=meeting.location,
                    )
                )

        if course.meetings and not schedulable_found:
            skipped_messages.append(
                f"Skipped all meetings for {course.title}: no schedulable meeting times found."
            )

        if include_final_exams:
            if course.final_exam is None:
                skipped_messages.append(
                    f"Skipped final exam for {course.title}: no final exam time listed."
                )
            else:
                csv_rows.append(
                    CsvRow(
                        subject=(
                            f"{course.subject_code} {course.course_number} "
                            f"{course.section_number} (Final Exam)"
                        ),
                        start_date=course.final_exam.exam_date.strftime("%m/%d/%Y"),
                        start_time=course.final_exam.start_time,
                        end_date=course.final_exam.exam_date.strftime("%m/%d/%Y"),
                        end_time=course.final_exam.end_time,
                        description=course.title,
                        location=course.final_exam.location,
                    )
                )

    return csv_rows, skipped_messages


def expand_weekdays(
    weekdays: tuple[str, ...],
    start_date: date,
    end_date: date,
) -> list[str]:
    dates: list[str] = []
    for weekday in weekdays:
        if weekday not in WEEKDAY_INDEX:
            continue

        target_weekday = WEEKDAY_INDEX[weekday]
        meeting_date = start_date
        while meeting_date.weekday() != target_weekday:
            meeting_date += timedelta(days=1)

        while meeting_date <= end_date:
            dates.append(meeting_date.strftime("%m/%d/%Y"))
            meeting_date += timedelta(days=7)

    return dates


def rows_to_csv_bytes(rows: list[CsvRow]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(CSV_HEADER)
    writer.writerows(row.as_list() for row in rows)
    return buffer.getvalue().encode("utf-8")


def convert_html_to_csv(
    html_text: str,
    start_date: date,
    end_date: date | None = None,
    repeat_events: bool = True,
    include_final_exams: bool = False,
) -> ConversionResult:
    effective_end_date = end_date if repeat_events else start_date + timedelta(days=6)
    if effective_end_date < start_date:
        raise ValueError("End date must be on or after the start date.")

    selected_course_ids = parse_selected_course_ids(html_text)
    if not selected_course_ids:
        raise ValueError(
            "No selected courses were found in the uploaded Schedule Builder HTML."
        )

    courses = [parse_course_record(html_text, course_id) for course_id in selected_course_ids]
    rows, skipped_messages = build_csv_rows(
        courses,
        start_date,
        effective_end_date,
        include_final_exams=include_final_exams,
    )
    return ConversionResult(rows=tuple(rows), skipped_messages=tuple(skipped_messages))
