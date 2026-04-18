# AI / Machine Learning and Data Analytics — Interview Prep Notes

## 1. Machine Learning Paradigms

### Supervised Learning
Learning from **labeled data** — the model learns a mapping from inputs to known outputs.
- **Use cases**: spam detection, image classification, price prediction
- **Key algorithms**: Linear Regression, Logistic Regression, SVM, Decision Trees, Random Forest, Neural Networks

### Unsupervised Learning
Learning from **unlabeled data** — the model discovers hidden patterns or structure.
- **Use cases**: customer segmentation, anomaly detection, topic modeling
- **Key algorithms**: K-Means, DBSCAN, Hierarchical Clustering, PCA, Autoencoders

### Reinforcement Learning
An agent learns by **interacting with an environment**, receiving rewards/penalties.
- **Key concepts**: Agent, Environment, State, Action, Reward, Policy, Value Function
- **Algorithms**: Q-Learning, Deep Q-Networks (DQN), Policy Gradient, PPO, A3C
- **Use cases**: Game playing (AlphaGo), robotics, recommendation systems

**Interview tip**: Be ready to explain when you'd choose each paradigm and give a concrete example.

---

## 2. Regression

### Linear Regression
Models a linear relationship between features and a continuous target.

```python
import numpy as np
from sklearn.linear_model import LinearRegression

X = np.array([[1], [2], [3], [4], [5]])
y = np.array([2.1, 4.0, 5.8, 8.1, 9.9])

model = LinearRegression()
model.fit(X, y)
print(f"Coefficient: {model.coef_[0]:.2f}, Intercept: {model.intercept_:.2f}")
# Coefficient: 1.97, Intercept: 0.08
```

- **Assumptions**: Linearity, independence, homoscedasticity, normality of residuals
- **Loss function**: Mean Squared Error (MSE) = (1/n) Σ(yᵢ - ŷᵢ)²
- **Regularization**: Ridge (L2), Lasso (L1), ElasticNet (L1+L2)

### Logistic Regression
Despite the name, it's a **classification** algorithm. Uses the sigmoid function to output probabilities.

```python
from sklearn.linear_model import LogisticRegression
from sklearn.datasets import make_classification

X, y = make_classification(n_samples=1000, n_features=10, random_state=42)
model = LogisticRegression()
model.fit(X, y)
print(f"Accuracy: {model.score(X, y):.3f}")
```

- **Sigmoid**: σ(z) = 1 / (1 + e⁻ᶻ)
- **Loss function**: Binary Cross-Entropy
- **Multiclass**: One-vs-Rest (OvR) or Softmax (multinomial)

### Polynomial Regression
Extends linear regression by adding polynomial features: y = β₀ + β₁x + β₂x² + ... + βₙxⁿ

```python
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline

model = make_pipeline(PolynomialFeatures(degree=3), LinearRegression())
model.fit(X, y)
```

**Watch out**: High-degree polynomials overfit easily. Use cross-validation to select degree.

---

## 3. Classification Algorithms

### Support Vector Machines (SVM)
Finds the **maximum-margin hyperplane** that separates classes.
- **Kernel trick**: Maps data to higher dimensions (RBF, polynomial, sigmoid)
- **C parameter**: Controls regularization (high C = hard margin, low C = soft margin)
- **Best for**: Small-to-medium datasets, high-dimensional spaces

### Decision Trees
Recursive partitioning using feature thresholds.
- **Splitting criteria**: Gini impurity, Information gain (entropy)
- **Gini**: 1 − Σpᵢ²
- **Entropy**: −Σpᵢ log₂(pᵢ)
- **Prone to overfitting** — use pruning or ensemble methods

### Random Forest
Ensemble of decision trees using **bagging** (bootstrap aggregating).
- Each tree trained on a random subset of data AND features
- Reduces variance while maintaining low bias
- **Feature importance** is a key benefit

```python
from sklearn.ensemble import RandomForestClassifier

rf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
rf.fit(X_train, y_train)

# Feature importance
for name, imp in zip(feature_names, rf.feature_importances_):
    print(f"{name}: {imp:.4f}")
```

### K-Nearest Neighbors (KNN)
Instance-based learning — classifies based on the majority vote of k nearest neighbors.
- **Distance metrics**: Euclidean, Manhattan, Minkowski
- **Choosing k**: Too small → noisy, too large → over-smoothed. Use cross-validation.
- **Curse of dimensionality**: Performance degrades in high dimensions

---

## 4. Neural Networks

### Perceptron
Single-layer neural unit: output = activation(Σ wᵢxᵢ + b)

### Backpropagation
Algorithm to compute gradients via the **chain rule**, propagating errors backward through the network.

### Activation Functions
| Function | Formula | Range | Use Case |
|----------|---------|-------|----------|
| Sigmoid | 1/(1+e⁻ˣ) | (0,1) | Binary output |
| Tanh | (eˣ−e⁻ˣ)/(eˣ+e⁻ˣ) | (−1,1) | Hidden layers |
| ReLU | max(0,x) | [0,∞) | Default for hidden layers |
| Leaky ReLU | max(αx,x) | (−∞,∞) | Avoids dead neurons |
| Softmax | eˣⁱ/Σeˣʲ | (0,1) | Multi-class output |

### Gradient Descent Variants
- **Batch GD**: Uses entire dataset per step — slow but stable
- **Stochastic GD (SGD)**: One sample per step — noisy but fast
- **Mini-batch GD**: Compromise — standard in practice (batch size 32–256)
- **Optimizers**: Adam (adaptive learning rate, momentum), RMSProp, AdaGrad

```python
import torch
import torch.nn as nn

class SimpleNN(nn.Module):
    def __init__(self, input_dim, hidden_dim, output_dim):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        return self.fc2(self.relu(self.fc1(x)))

model = SimpleNN(10, 64, 2)
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
criterion = nn.CrossEntropyLoss()
```

---

## 5. Deep Learning Architectures

### Convolutional Neural Networks (CNNs)
Designed for **spatial data** (images, video).
- **Convolution layers**: Extract local features via learnable filters
- **Pooling layers**: Downsample (max pooling, average pooling)
- **Architecture pattern**: Conv → ReLU → Pool → ... → Flatten → FC → Output
- **Famous architectures**: LeNet, AlexNet, VGG, ResNet (skip connections), Inception

### Recurrent Neural Networks (RNNs)
Process **sequential data** with hidden state memory.
- **Problem**: Vanishing/exploding gradients on long sequences

### Long Short-Term Memory (LSTM)
Solves RNN gradient issues with **gates**: forget, input, output.
- **Cell state**: Long-term memory highway
- **Use cases**: Time series, language modeling, speech recognition

### Transformers
The dominant architecture in modern AI. Based entirely on **self-attention**.
- **Self-attention**: Each token attends to all other tokens: Attention(Q,K,V) = softmax(QKᵀ/√dₖ)V
- **Multi-head attention**: Multiple attention heads capture different relationships
- **Positional encoding**: Injects sequence order information
- **Architecture**: Encoder-decoder (original), encoder-only (BERT), decoder-only (GPT)

### Attention Mechanism
Allows the model to focus on relevant parts of the input.
- **Scaled dot-product attention**: Core building block
- **Cross-attention**: Decoder attends to encoder output
- **Self-attention**: Sequence attends to itself

---

## 6. NLP Basics

### Tokenization
Breaking text into tokens (words, subwords, characters).
- **Word-level**: Simple but large vocabulary, can't handle OOV words
- **Subword**: BPE (Byte Pair Encoding), WordPiece, SentencePiece — best tradeoff
- **Character-level**: Small vocab but loses semantic meaning

### Embeddings
Dense vector representations of tokens.
- **Word2Vec**: Skip-gram (predict context from word) and CBOW (predict word from context)
- **GloVe**: Global co-occurrence statistics
- **Properties**: king − man + woman ≈ queen (semantic arithmetic)

### BERT (Bidirectional Encoder Representations from Transformers)
Pretrained on masked language modeling (MLM) and next sentence prediction (NSP).
- **Bidirectional context** — looks at both left and right context
- **Fine-tuning**: Add task-specific head on top of pretrained BERT
- **Variants**: RoBERTa, DistilBERT, ALBERT

```python
from transformers import BertTokenizer, BertModel

tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
model = BertModel.from_pretrained('bert-base-uncased')

inputs = tokenizer("Machine learning is fascinating", return_tensors="pt")
outputs = model(**inputs)
# outputs.last_hidden_state: [batch, seq_len, hidden_dim=768]
```

---

## 7. Evaluation Metrics

### Confusion Matrix
|  | Predicted Positive | Predicted Negative |
|--|---|---|
| **Actual Positive** | True Positive (TP) | False Negative (FN) |
| **Actual Negative** | False Positive (FP) | True Negative (TN) |

### Key Metrics
- **Accuracy** = (TP + TN) / (TP + TN + FP + FN) — misleading on imbalanced data
- **Precision** = TP / (TP + FP) — "Of predicted positives, how many are correct?"
- **Recall (Sensitivity)** = TP / (TP + FN) — "Of actual positives, how many did we catch?"
- **F1 Score** = 2 × (Precision × Recall) / (Precision + Recall) — harmonic mean
- **Specificity** = TN / (TN + FP)

### AUC-ROC
- **ROC Curve**: True Positive Rate vs False Positive Rate at varying thresholds
- **AUC**: Area Under the ROC Curve (0.5 = random, 1.0 = perfect)
- **When to use**: Binary classification, comparing models, threshold-independent evaluation

```python
from sklearn.metrics import classification_report, roc_auc_score

print(classification_report(y_true, y_pred))
auc = roc_auc_score(y_true, y_proba)
print(f"AUC-ROC: {auc:.3f}")
```

**Interview tip**: If asked "which metric would you use?", always ask about the **business context**. Medical diagnosis → high recall. Spam filter → high precision.

---

## 8. Overfitting, Underfitting, and Bias-Variance Tradeoff

### Overfitting (High Variance)
Model memorizes training data, fails on unseen data.
- **Signs**: Large gap between training and validation performance
- **Solutions**: More data, regularization (L1/L2, dropout), simpler model, early stopping, data augmentation

### Underfitting (High Bias)
Model is too simple to capture underlying patterns.
- **Signs**: Poor performance on both training and validation
- **Solutions**: More features, more complex model, reduce regularization, train longer

### Bias-Variance Tradeoff
- **Bias**: Error from overly simplistic assumptions
- **Variance**: Error from sensitivity to training data fluctuations
- **Total Error** = Bias² + Variance + Irreducible Error
- **Sweet spot**: Minimize both — use cross-validation to find it

### Cross-Validation
- **K-Fold**: Split data into k folds, train on k−1, validate on 1, rotate
- **Stratified K-Fold**: Preserves class distribution in each fold
- **Leave-One-Out (LOO)**: k = n, computationally expensive

```python
from sklearn.model_selection import cross_val_score

scores = cross_val_score(model, X, y, cv=5, scoring='f1_weighted')
print(f"Mean F1: {scores.mean():.3f} ± {scores.std():.3f}")
```

---

## 9. Feature Engineering and Dimensionality Reduction

### Feature Engineering
- **Encoding categoricals**: One-hot, label encoding, target encoding
- **Scaling**: StandardScaler (z-score), MinMaxScaler, RobustScaler (outlier-resistant)
- **Missing values**: Imputation (mean/median/mode), indicator variables, model-based
- **Feature creation**: Interaction terms, polynomial features, domain-specific features
- **Feature selection**: Correlation analysis, mutual information, recursive feature elimination

### PCA (Principal Component Analysis)
Linear dimensionality reduction that finds directions of maximum variance.
- Projects data onto **principal components** (eigenvectors of covariance matrix)
- Choose components that explain ≥ 95% of variance
- **Limitation**: Linear only, hard to interpret

### t-SNE (t-distributed Stochastic Neighbor Embedding)
Non-linear dimensionality reduction for **visualization** (2D/3D).
- Preserves local structure (nearby points stay nearby)
- **Not deterministic** — results vary with random seed and perplexity
- **Not for feature reduction** — use PCA for that

```python
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

pca = PCA(n_components=0.95)  # Keep 95% variance
X_pca = pca.fit_transform(X)
print(f"Reduced from {X.shape[1]} to {X_pca.shape[1]} dimensions")

tsne = TSNE(n_components=2, perplexity=30, random_state=42)
X_2d = tsne.fit_transform(X)
```

---

## 10. Clustering

### K-Means
Partition data into k clusters by minimizing within-cluster sum of squares.
- **Algorithm**: Initialize centroids → assign points → update centroids → repeat
- **Choosing k**: Elbow method, silhouette score
- **Limitations**: Assumes spherical clusters, sensitive to initialization (use k-means++)

### DBSCAN (Density-Based Spatial Clustering)
Groups dense regions separated by sparse regions.
- **Parameters**: eps (neighborhood radius), min_samples
- **Advantages**: No k needed, handles arbitrary shapes, identifies outliers
- **Limitation**: Struggles with varying density clusters

### Hierarchical Clustering
Builds a tree (dendrogram) of clusters — agglomerative (bottom-up) or divisive (top-down).
- **Linkage**: Single, complete, average, Ward's method
- **Advantage**: Dendrogram shows cluster hierarchy, no k needed upfront

```python
from sklearn.cluster import KMeans, DBSCAN

kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
labels_km = kmeans.fit_predict(X)

dbscan = DBSCAN(eps=0.5, min_samples=5)
labels_db = dbscan.fit_predict(X)
```

---

## 11. Data Preprocessing with Pandas/NumPy

```python
import pandas as pd
import numpy as np

# Loading and inspecting
df = pd.read_csv('data.csv')
df.head(), df.info(), df.describe()
df.isnull().sum()            # Missing values per column
df.duplicated().sum()         # Duplicate rows

# Handling missing values
df['col'].fillna(df['col'].median(), inplace=True)
df.dropna(subset=['critical_col'], inplace=True)

# Encoding
df['category_encoded'] = df['category'].map({'A': 0, 'B': 1, 'C': 2})
df = pd.get_dummies(df, columns=['category'], drop_first=True)

# Feature scaling
from sklearn.preprocessing import StandardScaler
scaler = StandardScaler()
df[['feat1', 'feat2']] = scaler.fit_transform(df[['feat1', 'feat2']])

# Useful pandas operations
df.groupby('category')['value'].agg(['mean', 'std', 'count'])
df.pivot_table(values='revenue', index='region', columns='product', aggfunc='sum')
df['col'].value_counts(normalize=True)
```

### NumPy Essentials
```python
arr = np.array([[1, 2, 3], [4, 5, 6]])
arr.shape, arr.dtype, arr.reshape(3, 2)
np.dot(a, b)                 # Matrix multiplication
np.linalg.inv(matrix)        # Matrix inverse
np.linalg.eig(matrix)        # Eigenvalues and eigenvectors
np.random.seed(42)
np.random.normal(0, 1, 1000) # Normal distribution samples
```

---

## 12. A/B Testing

### Process
1. **Formulate hypothesis**: H₀ (no difference) vs H₁ (there is a difference)
2. **Determine sample size**: Use power analysis (effect size, significance level α, power 1−β)
3. **Randomize**: Randomly assign users to control (A) and treatment (B)
4. **Run experiment**: Collect data for sufficient duration
5. **Analyze**: Statistical test to accept/reject H₀

### Key Concepts
- **p-value**: Probability of observing the result if H₀ is true. Reject H₀ if p < α (typically 0.05)
- **Type I error (α)**: False positive — rejecting H₀ when it's true
- **Type II error (β)**: False negative — failing to reject H₀ when it's false
- **Statistical power** = 1 − β (typically 0.8)
- **Effect size**: Practical significance of the difference

```python
from scipy import stats

# Two-sample t-test
control = np.random.normal(10.0, 2.0, 1000)
treatment = np.random.normal(10.5, 2.0, 1000)

t_stat, p_value = stats.ttest_ind(control, treatment)
print(f"t-statistic: {t_stat:.3f}, p-value: {p_value:.4f}")
if p_value < 0.05:
    print("Reject H₀: Statistically significant difference")
```

**Common pitfalls**: Peeking at results too early, not accounting for multiple comparisons (Bonferroni correction), ignoring practical significance, Simpson's paradox.

---

## 13. Common Interview Questions

1. **"Explain the bias-variance tradeoff."** → Bias = underfitting, variance = overfitting. Total error = bias² + variance + noise. Need to find the sweet spot.

2. **"How do you handle imbalanced datasets?"** → SMOTE, undersampling, class weights, different metrics (F1, AUC-ROC), anomaly detection framing.

3. **"When would you use Random Forest over Gradient Boosting?"** → RF is less prone to overfitting, parallelizable, good baseline. GB (XGBoost/LightGBM) often achieves higher accuracy but needs careful tuning.

4. **"Explain how a transformer works."** → Self-attention lets each token attend to all others. Multi-head attention captures different patterns. Positional encoding preserves order. No recurrence — fully parallelizable.

5. **"What's the difference between L1 and L2 regularization?"** → L1 (Lasso) drives weights to exactly zero (feature selection). L2 (Ridge) shrinks weights uniformly (never zero). ElasticNet combines both.

6. **"How do you choose between precision and recall?"** → Depends on the cost of errors. Medical diagnosis: optimize recall (don't miss sick patients). Spam detection: optimize precision (don't misclassify important emails).

7. **"Explain gradient descent and its variants."** → Iteratively update weights in the direction that minimizes loss. Batch (full dataset), SGD (one sample), mini-batch (compromise). Adam optimizer adapts learning rate per parameter.

---

## 14. Best Practices and Pitfalls

### Best Practices
- Always split data into train/validation/test **before** any preprocessing
- Use stratified splits for classification
- Scale features but **don't scale the target** in regression
- Start simple (logistic regression, random forest) before going deep
- Log experiments — track hyperparameters, metrics, and data versions
- Validate on a holdout set that mirrors production data distribution

### Common Pitfalls
- **Data leakage**: Using future information or test data in training
- **Fitting scaler on test data**: Fit on train, transform on test
- **Ignoring class imbalance**: Accuracy can be misleading (99% accuracy on 99/1 split)
- **Not checking assumptions**: Linear regression assumes linearity and normality
- **Overfitting to validation set**: Tune on validation, report on test
- **Correlation ≠ causation**: Features may be correlated without causal relationship
