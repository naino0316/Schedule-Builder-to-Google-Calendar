"""Run with: streamlit run app.py"""

from datetime import date

import streamlit as st

from main_modified import convert_html_to_csv, load_html_from_bytes


st.set_page_config(page_title="Schedule Builder to Google Calendar", page_icon="calendar")

st.title("Schedule Builder to Google Calendar")
st.write(
    "Upload your `Schedule Builder.html`, choose the overall date range, "
    "and download a Google Calendar-compatible `output_list.csv`."
)
with st.expander("Tutorial: How to use this app", expanded=True):
    st.markdown(
        "\n".join(
            [
                "1. Log in to Schedule Builder and open the quarter you want to export.",
                "2. Save the Schedule Builder webpage to your computer with `Ctrl+S` on Windows or `Cmd+S` on Mac.",
                "3. Upload that saved HTML file here, choose the quarter start and end dates, and generate `output_list.csv`.",
                "4. In Google Calendar, open `Settings > Import & export` and import the generated CSV file.",
            ]
        )
    )

uploaded_file = st.file_uploader(
    "Choose your Schedule Builder HTML file",
    type=["html", "htm"],
)

default_start = date.today()
default_end = default_start

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Quarter start date", value=default_start)
with col2:
    end_date = st.date_input("Quarter end date", value=default_end)

generate_clicked = st.button("Generate CSV", type="primary")

if generate_clicked:
    if uploaded_file is None:
        st.error("Please upload a Schedule Builder HTML file first.")
    elif end_date < start_date:
        st.error("End date must be on or after the start date.")
    else:
        try:
            html_text = load_html_from_bytes(uploaded_file.getvalue())
            result = convert_html_to_csv(html_text, start_date, end_date)
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
                st.warning("Some meetings were skipped because they had no schedulable time.")
                for message in result.skipped_messages:
                    st.write(f"- {message}")
