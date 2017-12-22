import React, { Component } from 'react';
import WalletList from './widgets/wallet_list.js';
import NewWalletForm from './widgets/new_wallet_form.js';
import Blockcount from './widgets/blockcount.js';
import {axiosInstance} from './tools.js';
import {Tabs, Tab} from 'material-ui/Tabs';

const styles = {
  headline: {
    fontSize: 24,
    paddingTop: 16,
    marginBottom: 12,
    fontWeight: 400,
  },
};

class ChooseWallet extends Component {

  constructor(props) {
    super(props);
    this.state = {
      'wallets': null
    }
    this.getWallets = this.getWallets.bind(this);
  } 

  componentDidMount() {
    this.getWallets();
  }

  getWallets() {
    axiosInstance.get("/wallets").then((response) => {
      let data = response.data;
      console.log(data);
      if(data.hasOwnProperty('wallets')) {
        this.setState((state) => {
          state['wallets'] = Object.keys(data.wallets);
          return state;
        });
      }
    });
  }

  render() {
    return (
      <div>
        <Tabs>
          <Tab label="New Wallet" >
            <NewWalletForm refresh={this.getWallets} notify={this.props.notify}/>
          </Tab>
          <Tab label="Choose a Wallet" >
            <WalletList wallets={this.state.wallets} notify={this.props.notify}/>
          </Tab>
          <Tab label="Restore Wallet">
            <div>
              <h2 style={styles.headline}>Restore Wallet</h2>
              <p>
                Here will be an upload form to restore an earlier wallet
              </p>
            </div>
          </Tab>
        </Tabs>
        <Blockcount socket={this.props.socket}/>
      </div>
    );
  }
}

export default ChooseWallet;