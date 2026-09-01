# METIS Kaggle model export

1. Create/upload a `recovery_events.csv` Kaggle dataset with the columns documented in `train_models.py`.
2. Add the dataset to a Kaggle notebook, copy `train_models.py` into a notebook cell (or upload it), and run it.
3. Download `propensity_model.pkl`, `intervention_model.pkl`, and `fatigue_model.pkl` from `/kaggle/working`.
4. Put all three files in `backend/models/`, then restart the backend container.

The API automatically discovers these names. `/health` reports `"ml_mode":"trained"` after a successful load; it remains in stub mode otherwise.
