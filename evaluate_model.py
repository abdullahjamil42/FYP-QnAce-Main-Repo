import torch
from torch.utils.data import Dataset, DataLoader
from transformers import BertTokenizer, BertForSequenceClassification
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns

class InterviewDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_length=128):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = self.labels[idx]
        
        encoding = self.tokenizer(
            text,
            add_special_tokens=True,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'label': torch.tensor(label, dtype=torch.long)
        }

def evaluate_model(model, dataloader, device):
    """Evaluate model on a dataset"""
    model.eval()
    predictions = []
    true_labels = []
    total_loss = 0
    
    with torch.no_grad():
        for batch in dataloader:
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['label'].to(device)
            
            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels
            )
            
            total_loss += outputs.loss.item()
            logits = outputs.logits
            preds = torch.argmax(logits, dim=1)
            
            predictions.extend(preds.cpu().numpy())
            true_labels.extend(labels.cpu().numpy())
    
    avg_loss = total_loss / len(dataloader)
    accuracy = accuracy_score(true_labels, predictions)
    precision, recall, f1, _ = precision_recall_fscore_support(
        true_labels, predictions, average='weighted'
    )
    
    return {
        'loss': avg_loss,
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'predictions': predictions,
        'true_labels': true_labels
    }

def plot_performance_comparison(train_metrics, val_metrics, test_metrics):
    """Plot performance metrics across datasets"""
    metrics = ['accuracy', 'precision', 'recall', 'f1']
    train_vals = [train_metrics[m] for m in metrics]
    val_vals = [val_metrics[m] for m in metrics]
    test_vals = [test_metrics[m] for m in metrics]
    
    x = np.arange(len(metrics))
    width = 0.25
    
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(x - width, train_vals, width, label='Training', alpha=0.8)
    ax.bar(x, val_vals, width, label='Validation', alpha=0.8)
    ax.bar(x + width, test_vals, width, label='Test', alpha=0.8)
    
    ax.set_ylabel('Score')
    ax.set_title('Model Performance: Training vs Validation vs Test')
    ax.set_xticks(x)
    ax.set_xticklabels(metrics)
    ax.legend()
    ax.set_ylim([0, 1.1])
    
    # Add value labels on bars
    for i, v in enumerate(train_vals):
        ax.text(i - width, v + 0.02, f'{v:.3f}', ha='center', va='bottom', fontsize=8)
    for i, v in enumerate(val_vals):
        ax.text(i, v + 0.02, f'{v:.3f}', ha='center', va='bottom', fontsize=8)
    for i, v in enumerate(test_vals):
        ax.text(i + width, v + 0.02, f'{v:.3f}', ha='center', va='bottom', fontsize=8)
    
    plt.tight_layout()
    plt.savefig('model_performance_comparison.png', dpi=300)
    plt.close()

def plot_loss_comparison(train_loss, val_loss, test_loss):
    """Plot loss comparison"""
    fig, ax = plt.subplots(figsize=(8, 6))
    datasets = ['Training', 'Validation', 'Test']
    losses = [train_loss, val_loss, test_loss]
    colors = ['#2ecc71', '#3498db', '#e74c3c']
    
    bars = ax.bar(datasets, losses, color=colors, alpha=0.7)
    ax.set_ylabel('Loss')
    ax.set_title('Loss Comparison Across Datasets')
    ax.set_ylim([0, max(losses) * 1.2])
    
    # Add value labels
    for bar, loss in zip(bars, losses):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{loss:.4f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('loss_comparison.png', dpi=300)
    plt.close()

def plot_confusion_matrices(train_metrics, val_metrics, test_metrics):
    """Plot confusion matrices for all datasets"""
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    datasets = [
        ('Training', train_metrics),
        ('Validation', val_metrics),
        ('Test', test_metrics)
    ]
    
    for ax, (name, metrics) in zip(axes, datasets):
        cm = confusion_matrix(metrics['true_labels'], metrics['predictions'])
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax)
        ax.set_title(f'{name} Set Confusion Matrix')
        ax.set_ylabel('True Label')
        ax.set_xlabel('Predicted Label')
    
    plt.tight_layout()
    plt.savefig('confusion_matrices.png', dpi=300)
    plt.close()

def analyze_overfitting_underfitting(train_metrics, val_metrics, test_metrics):
    """Analyze and provide diagnosis"""
    print("\n" + "="*60)
    print("OVERFITTING/UNDERFITTING ANALYSIS")
    print("="*60)
    
    # Calculate gaps
    train_val_acc_gap = train_metrics['accuracy'] - val_metrics['accuracy']
    train_test_acc_gap = train_metrics['accuracy'] - test_metrics['accuracy']
    val_test_acc_gap = val_metrics['accuracy'] - test_metrics['accuracy']
    
    train_val_loss_gap = val_metrics['loss'] - train_metrics['loss']
    
    print(f"\n[*] Performance Gaps:")
    print(f"   Training-Validation Accuracy Gap: {train_val_acc_gap:.4f}")
    print(f"   Training-Test Accuracy Gap: {train_test_acc_gap:.4f}")
    print(f"   Validation-Test Accuracy Gap: {val_test_acc_gap:.4f}")
    print(f"   Validation-Training Loss Gap: {train_val_loss_gap:.4f}")
    
    print(f"\n[*] Absolute Metrics:")
    print(f"   Training Accuracy: {train_metrics['accuracy']:.4f}")
    print(f"   Validation Accuracy: {val_metrics['accuracy']:.4f}")
    print(f"   Test Accuracy: {test_metrics['accuracy']:.4f}")
    print(f"   Training Loss: {train_metrics['loss']:.4f}")
    print(f"   Validation Loss: {val_metrics['loss']:.4f}")
    print(f"   Test Loss: {test_metrics['loss']:.4f}")
    
    # Diagnosis
    print(f"\n[*] DIAGNOSIS:")
    
    # Check for overfitting
    if train_val_acc_gap > 0.1:
        print("   [!] SEVERE OVERFITTING DETECTED")
        print("      - Large gap between training and validation accuracy")
        print("      - Model memorizes training data but doesn't generalize")
    elif train_val_acc_gap > 0.05:
        print("   [!] MODERATE OVERFITTING DETECTED")
        print("      - Noticeable gap between training and validation accuracy")
    elif train_val_acc_gap > 0.02:
        print("   [!] MILD OVERFITTING")
        print("      - Small gap between training and validation accuracy")
    else:
        print("   [+] No significant overfitting detected")
    
    # Check for underfitting
    if train_metrics['accuracy'] < 0.7:
        print("   [!] UNDERFITTING DETECTED")
        print("      - Low training accuracy indicates model hasn't learned patterns")
    elif train_metrics['accuracy'] < 0.8:
        print("   [!] POSSIBLE UNDERFITTING")
        print("      - Training accuracy could be improved")
    else:
        print("   [+] Model appears to have learned training data well")
    
    # Check generalization
    if abs(val_test_acc_gap) < 0.03:
        print("   [+] Good generalization: similar validation and test performance")
    else:
        print("   [!] Generalization concern: validation and test performance differ")
    
    # Recommendations
    print(f"\n[*] RECOMMENDATIONS:")
    if train_val_acc_gap > 0.05:
        print("   - Add regularization (dropout, weight decay)")
        print("   - Use data augmentation")
        print("   - Reduce model complexity")
        print("   - Collect more training data")
        print("   - Apply early stopping")
    
    if train_metrics['accuracy'] < 0.8:
        print("   - Increase model capacity")
        print("   - Train for more epochs")
        print("   - Adjust learning rate")
        print("   - Check data quality and preprocessing")
    
    if val_metrics['accuracy'] > 0.85 and train_val_acc_gap < 0.05:
        print("   [+] Model is performing well! Consider deployment.")
    
    print("="*60 + "\n")

def main():
    # Configuration
    MODEL_PATH = '../fine-tuned-bert-model'
    DATA_PATH = 'Interview_Dataset.csv'
    BATCH_SIZE = 16
    MAX_LENGTH = 128
    
    print("Loading model and tokenizer...")
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    tokenizer = BertTokenizer.from_pretrained(MODEL_PATH)
    model = BertForSequenceClassification.from_pretrained(MODEL_PATH)
    model.to(device)
    
    print("Loading dataset...")
    df = pd.read_csv(DATA_PATH)
    
    # The dataset has 'answer' and 'label' columns based on the CSV structure
    texts = df['answer'].values
    labels = df['label'].values
    
    print(f"Dataset loaded: {len(texts)} samples")
    print(f"Label distribution: {np.bincount(labels)}")
    
    # Split data
    train_texts, temp_texts, train_labels, temp_labels = train_test_split(
        texts, labels, test_size=0.3, random_state=42, stratify=labels
    )
    val_texts, test_texts, val_labels, test_labels = train_test_split(
        temp_texts, temp_labels, test_size=0.5, random_state=42, stratify=temp_labels
    )
    
    print(f"\nDataset splits:")
    print(f"  Training: {len(train_texts)} samples")
    print(f"  Validation: {len(val_texts)} samples")
    print(f"  Test: {len(test_texts)} samples")
    
    # Create datasets and dataloaders
    train_dataset = InterviewDataset(train_texts, train_labels, tokenizer, MAX_LENGTH)
    val_dataset = InterviewDataset(val_texts, val_labels, tokenizer, MAX_LENGTH)
    test_dataset = InterviewDataset(test_texts, test_labels, tokenizer, MAX_LENGTH)
    
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=False)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)
    
    # Evaluate on all splits
    print("\nEvaluating on training set...")
    train_metrics = evaluate_model(model, train_loader, device)
    
    print("Evaluating on validation set...")
    val_metrics = evaluate_model(model, val_loader, device)
    
    print("Evaluating on test set...")
    test_metrics = evaluate_model(model, test_loader, device)
    
    # Print results
    print("\n" + "="*60)
    print("EVALUATION RESULTS")
    print("="*60)
    print(f"\nTraining Set:")
    print(f"  Loss: {train_metrics['loss']:.4f}")
    print(f"  Accuracy: {train_metrics['accuracy']:.4f}")
    print(f"  Precision: {train_metrics['precision']:.4f}")
    print(f"  Recall: {train_metrics['recall']:.4f}")
    print(f"  F1-Score: {train_metrics['f1']:.4f}")
    
    print(f"\nValidation Set:")
    print(f"  Loss: {val_metrics['loss']:.4f}")
    print(f"  Accuracy: {val_metrics['accuracy']:.4f}")
    print(f"  Precision: {val_metrics['precision']:.4f}")
    print(f"  Recall: {val_metrics['recall']:.4f}")
    print(f"  F1-Score: {val_metrics['f1']:.4f}")
    
    print(f"\nTest Set:")
    print(f"  Loss: {test_metrics['loss']:.4f}")
    print(f"  Accuracy: {test_metrics['accuracy']:.4f}")
    print(f"  Precision: {test_metrics['precision']:.4f}")
    print(f"  Recall: {test_metrics['recall']:.4f}")
    print(f"  F1-Score: {test_metrics['f1']:.4f}")
    
    # Analyze overfitting/underfitting
    analyze_overfitting_underfitting(train_metrics, val_metrics, test_metrics)
    
    # Generate visualizations
    print("Generating visualizations...")
    plot_performance_comparison(train_metrics, val_metrics, test_metrics)
    plot_loss_comparison(train_metrics['loss'], val_metrics['loss'], test_metrics['loss'])
    plot_confusion_matrices(train_metrics, val_metrics, test_metrics)
    
    print("✅ Evaluation complete! Check the generated PNG files for visualizations.")

if __name__ == "__main__":
    main()
