import React, { Component } from 'react';
import WalletList from './widgets/wallet_list.js';
import NewWalletForm from './widgets/new_wallet_form.js';
import {Card, CardHeader, CardText} from 'material-ui/Card';
import Blockcount from './widgets/blockcount.js';
import {axiosInstance} from './tools.js';
import {Tabs, Tab} from 'material-ui/Tabs';

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
            <Card style={{"margin":16}}>
              <CardHeader
                title="Restore a Wallet"
                subtitle="Select a wallet that you backed up earlier"
              />
              <CardText>
                This feature will be available in next releases.
              </CardText>
            </Card>
          </Tab>
        </Tabs>
        <Blockcount socket={this.props.socket} notify={this.props.notify}/>
      </div>
    );
  }
}

export default ChooseWallet;