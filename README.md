# Surbhandar · Music Atlas

A small Streamlit app for exploring 10,819 Bangla recordings. Search by song,
artist, album, or an original filename. Click a point or a search result to see
its 25 nearest tracks, then follow any neighbour to continue exploring.

## Run

Use Python 3.12 or newer:

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

For Streamlit Community Cloud, select this private repository, `main`, and
`app.py`. Make the **app** public if it should open without login; keep the
**repository** private. Do not enable static serving for the `data` directory.

## Sharing boundary

This repository starts fresh and contains only the browsing application and a
reduced, reviewed catalogue. It contains no source audio, extraction pipeline,
raw features, embeddings, cloud paths, credentials, recording hashes, or source
channel identifiers. Original filenames remain server-side search aliases.

The server holds the complete catalogue and ordered neighbour table. The map
receives coordinates, colour bands, and opaque numeric point IDs. Names and
neighbours are sent only for the current selection and visible search results.
Viewing the app does not grant GitHub repository access.

This is disclosure reduction, not copy prevention. Displayed coordinates and
returned results can be captured; repeated browsing can collect more results.
The no-login app has no restriction on who can view it once its URL is shared.
This app's neighbour lists preserve the original ranks and are not calculated
from distances on the 3D screen.

## Check

```sh
.venv/bin/python test_atlas.py
```

The check validates every recording and neighbourhood, multilingual search,
the browser payload boundary, and the native Streamlit controls.

## Design references

- [Streamlit layouts and containers](https://docs.streamlit.io/develop/concepts/design/layouts-and-containers)
- [Designing Streamlit apps for users](https://blog.streamlit.io/designing-streamlit-apps-for-the-user-part-ii/)
- [Native bidirectional components](https://docs.streamlit.io/develop/api-reference/custom-components/st.components.v2.component)
