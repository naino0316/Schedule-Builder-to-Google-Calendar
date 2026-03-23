"""Run with: streamlit run app.py"""

from datetime import date

import streamlit as st

from main_modified import convert_html_to_csv, load_html_from_bytes


st.set_page_config(page_title="Schedule Builder to Google Calendar", page_icon="calendar")

st.title("Schedule Builder to Google Calendar")
st.write(
    "Upload your `Schedule Builder.html`, choose your export settings, "
    "and download a Google Calendar-compatible `output_list.csv`."
)
with st.expander("Tutorial: How to use this app", expanded=True):
    st.markdown(
        "\n".join(
            [
                "1. Log in to Schedule Builder and open the quarter you want to export.",
                "2. Save the Schedule Builder webpage to your computer with `Ctrl+S` on Windows or `Cmd+S` on Mac.",
                "3. Upload that saved HTML file here, choose your export options in the sidebar, and generate `output_list.csv`.",
                "4. In Google Calendar, open `Settings > Import & export` and import the generated CSV file.",
            ]
        )
    )

uploaded_file = st.file_uploader(
    "Choose your Schedule Builder HTML file",
    type=["html", "htm"],
)

default_start = date(2026, 3, 28)
default_end = date(2026, 6, 4)

st.sidebar.header("Export Options")
repeat_events = st.sidebar.checkbox("Repeat events", value=False)
include_final_exams = st.sidebar.checkbox("Include final exams", value=True)
start_date = st.sidebar.date_input("Quarter start date", value=default_start)
end_date = None
if repeat_events:
    end_date = st.sidebar.date_input("Quarter end date", value=default_end)
    st.sidebar.warning(
        "Repeated classes will be exported as separate events in Google Calendar. "
        "They will not be linked together as one recurring series."
    )
else:
    st.sidebar.caption("One-week mode exports events from the start date through the next 6 days.")

generate_clicked = st.button("Generate CSV", type="primary")

if generate_clicked:
    if uploaded_file is None:
        st.error("Please upload a Schedule Builder HTML file first.")
    elif repeat_events and end_date is not None and end_date < start_date:
        st.error("End date must be on or after the start date.")
    else:
        try:
            html_text = load_html_from_bytes(uploaded_file.getvalue())
            result = convert_html_to_csv(
                html_text,
                start_date,
                end_date=end_date,
                repeat_events=repeat_events,
                include_final_exams=include_final_exams,
            )
            csv_bytes = result.to_csv_bytes()
        except UnicodeDecodeError:
            st.error("The uploaded file could not be read as UTF-8 HTML.")
        except ValueError as error:
            st.error(str(error))
        except Exception as error:
            st.error(f"Something went wrong while processing the file: {error}")
        else:
            st.success("CSV generated successfully.")
            st.download_button(
                label="Download output_list.csv",
                data=csv_bytes,
                file_name="output_list.csv",
                mime="text/csv",
            )

            st.caption(f"Generated {len(result.rows)} calendar rows.")

            if result.skipped_messages:
                st.warning("Some events were skipped because they had no schedulable time or no listed final exam.")
                for message in result.skipped_messages:
                    st.write(f"- {message}")
