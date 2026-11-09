"""Demo + report for the Day 14 movie recommender.

Prints dataset stats, an example of learned similarity, RMSE against
two baselines, Precision@5 / Recall@5, sample recommendations for one
user, and the cold-start (new user) fallback.
"""

from recommender import (
    MOVIES,
    evaluate,
    generate_ratings,
    item_similarity,
    global_mean,
    popularity,
    predict,
    recommend,
    train_test_split,
    user_means,
)


def main():
    ratings, _ = generate_ratings()
    train, test = train_test_split(ratings)
    means = user_means(train)
    gmean = global_mean(train)
    sims = item_similarity(train)

    print("Movie recommender — item-based collaborative filtering")
    print(f"{len(ratings)} synthetic ratings, {len(MOVIES)} movies, "
          f"60 users ({len(train)} train / {len(test)} test)")
    print(f"Global mean rating: {gmean:.2f}")

    # Most-similar pair the model actually learned.
    pairs = sorted(
        ((s, i, j) for (i, j), s in sims.items() if i < j),
        reverse=True,
    )
    s, i, j = pairs[0]
    print(f"\nMost similar pair learned: '{MOVIES[i][0]}' ~ "
          f"'{MOVIES[j][0]}' (sim {s:.2f}) — "
          f"genres {MOVIES[i][1]} vs {MOVIES[j][1]}")

    results = evaluate(train, test, sims, means, gmean)
    print("\nHeld-out test results "
          f"({results['test_ratings']} ratings):")
    print(f"  model RMSE:       {results['model_rmse']:.3f}")
    print(f"  global-mean RMSE: {results['global_mean_rmse']:.3f}")
    print(f"  user-mean RMSE:   {results['user_mean_rmse']:.3f}")
    print(f"  Precision@5:      {results['precision_at_5']:.3f}")
    print(f"  Recall@5:         {results['recall_at_5']:.3f} "
          f"({results['users_evaluated']} users with a liked test movie)")

    user = 0
    print(f"\nTop 5 recommendations for user {user} "
          f"(mean rating {means[user]:.2f}):")
    for m, pred in recommend(user, train, sims, means, gmean):
        print(f"  {pred:.1f}★  {MOVIES[m][0]}  ({', '.join(MOVIES[m][1])})")

    print("\nCold start — a brand-new user gets the most popular movies:")
    for m, avg, count in popularity(train)[:5]:
        print(f"  {avg:.2f}★ ({count} ratings)  {MOVIES[m][0]}")

    # One concrete prediction, for the README example.
    u, m = 0, 3
    print(f"\nExample: user {u} is predicted to rate "
          f"'{MOVIES[m][0]}' {predict(u, m, train, sims, means, gmean):.2f}★")


if __name__ == "__main__":
    main()
