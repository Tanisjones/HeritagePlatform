"""
The contributions app hosts the contributor self-service API
(MyContributionsViewSet) over heritage.HeritageItem.

It has no models of its own: the original Contribution/ContributionReview
models were dead code from before the workflow merged into HeritageItem's
status machine (draft → pending → published/rejected), and were removed in
the F-hygiene pass (migration 0002 drops the tables).
"""
