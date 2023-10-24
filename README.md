LSTM networks can model customer journeys as sequences of touchpoints, offering insights into conversion funnels and potential retargeting leads. Leveraging sequence prediction abilities, LSTMs can predict touchpoint sequences, benefiting advertisers and marketers. To achieve this:

    Use Colab Jupyter notebook for model development.
    Authenticate in Colab to access data in GCP bucket.
    Download training data to Colab's /tmp directory.
    Train an encoder-decoder LSTM using Keras, using holdout data for testing.
    During testing, if the predicted sequence includes the word 'visit', label as 1 and compare to the actual sequence.
    Develop a confusion matrix from these results.
    Calculate model KPI.
    Save all work in /tmp directory and back it up in GCP bucket.