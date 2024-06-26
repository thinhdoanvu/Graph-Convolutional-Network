import torch
import torch.nn as nn
import numpy as np
import time

# Setup CUDA
def setup_cuda():
    # Setting seeds for reproducibility
    seed = 50
    torch.backends.cudnn.enabled = True
    torch.backends.cudnn.benchmark = True
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)

    return torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

def accuracy(output, labels):
    y_pred = output.max(1)[1].type_as(labels)
    correct = y_pred.eq(labels).double()
    correct = correct.sum()
    return correct / len(labels)


def training_loop(model, features, labels, adj, train_set_ind, val_set_ind, config):
    if config.cuda:
        model.cuda()
        adj = adj.cuda()
        features = features.cuda()
        labels = labels.cuda()

    optimizer = torch.optim.Adam(model.parameters(), lr=config.lr,
                                 weight_decay=config.weight_decay)
    criterion = nn.CrossEntropyLoss()

    validation_acc = []
    validation_loss = []

    if config.use_early_stopping:
        last_min_val_loss = float('inf')
        patience_counter = 0
        stopped_early = False

    t_start = time.time()
    for epoch in range(config.epochs):
        optimizer.zero_grad()
        model.train()

        y_pred = model(features, adj)
        train_loss = criterion(y_pred[train_set_ind], labels[train_set_ind])
        train_acc = accuracy(y_pred[train_set_ind], labels[train_set_ind])
        train_loss.backward()
        optimizer.step()

        with torch.no_grad():
            model.eval()
            val_loss = criterion(y_pred[val_set_ind], labels[val_set_ind])
            val_acc = accuracy(y_pred[val_set_ind], labels[val_set_ind])

            validation_loss.append(val_loss.item())
            validation_acc.append(val_acc)

            if config.use_early_stopping:
                if val_loss < last_min_val_loss:
                    last_min_val_loss = val_loss
                    patience_counter = 0
                else:
                    patience_counter += 1
                    if patience_counter == config.patience:
                        stopped_early = True
                        t_end = time.time()

        if not config.multiple_runs:
            print(" | ".join([f"Epoch: {epoch:4d}", f"Train loss: {train_loss.item():.3f}",
                              f"Train acc: {train_acc:.2f}",
                              f"Val loss: {val_loss.item():.3f}",
                              f"Val acc: {val_acc:.2f}"]))

        if config.use_early_stopping and stopped_early:
            break

    if (not config.multiple_runs) and config.use_early_stopping and stopped_early:
        print(f"EARLY STOPPING condition met. Stopped at epoch: {epoch}.")
    else:
        t_end = time.time()

    if not config.multiple_runs:
        print(f"Total training time: {t_end-t_start:.2f} seconds")

    return validation_acc, validation_loss


def evaluate_on_test(model, features, labels, adj, test_ind, config):
    if config.cuda:
        model.cuda()
        adj = adj.cuda()
        features = features.cuda()
        labels = labels.cuda()

    criterion = nn.CrossEntropyLoss()

    with torch.no_grad():
        model.eval()
        y_pred = model(features, adj)
        test_loss = criterion(y_pred[test_ind], labels[test_ind])
        test_acc = accuracy(y_pred[test_ind], labels[test_ind])

    if not config.multiple_runs:
        print()
        print(f"Test loss: {test_loss:.3f}  |  Test acc: {test_acc:.2f}")
        return y_pred
    else:
        return test_acc.item(), test_loss.item()

def multiple_runs(model, features, labels, adj, indices, config, training_loop, evaluate_on_test):
    train_set_ind, val_set_ind, test_set_ind = indices
    acc = []
    loss = []

    t1 = time.time()
    for i in range(config.num_of_runs):
        print("Run:", i+1)
        model.initialize_weights()
        training_loop(model, features, labels, adj,
                      train_set_ind, val_set_ind, config)

        acc_curr, loss_curr = evaluate_on_test(model, features, labels,
                                               adj, test_set_ind, config)
        acc.append(acc_curr)
        loss.append(loss_curr)

    print(f"ACC:  mean: {np.mean(acc):.2f} | std: {np.std(acc):.2f}")
    print(f"LOSS: mean: {np.mean(loss):.2f} | std: {np.std(loss):.2f}")
    print(f"Total training time: {time.time()-t1:.2f} seconds")

if __name__ == "__main__":

    # 1. Load config
    from config import config
    from utils.Getdataset import *
    features, labels, adj, edges = load_data(config)

    # 2. vusualize graph data
    from utils.visualization import *
    #set CPU
    config.cuda = False
    visualize_graph(edges, labels.cpu().tolist(), save=True)#True only one time

    # 3. training
    NUM_CLASSES = int(labels.max().item() + 1)
    train_set_ind, val_set_ind, test_set_ind = prepare_dataset(labels, NUM_CLASSES, config)
    from utils.model import GCN
    model = GCN(features.shape[1], config.hidden_dim, NUM_CLASSES, config.dropout, config.use_bias)

    if not config.multiple_runs:
        print("Started training with 1 run.",
              f"Early stopping: {'Yes' if config.use_early_stopping else 'No'}")
        val_acc, val_loss = training_loop(model, features, labels, adj, train_set_ind, val_set_ind, config)
        out_features = evaluate_on_test(model, features, labels, adj, test_set_ind, config)

        #visualize
        visualize_validation_performance(val_acc, val_loss)
        visualize_embedding_tSNE(labels, out_features, NUM_CLASSES)
    else:
        print(f"Started training with {config.num_of_runs} runs.",
              f"Early stopping: {'Yes' if config.use_early_stopping else 'No'}")
        multiple_runs(model, features, labels, adj,
                      [train_set_ind, val_set_ind, test_set_ind],
                      config, training_loop, evaluate_on_test)


