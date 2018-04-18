import React, { Component } from 'react';
import WalletList from './widgets/wallet_list.js';
import NewWalletForm from './widgets/new_wallet_form.js';
import {Card, CardHeader, CardText} from 'material-ui/Card';
import Blockcount from './widgets/blockcount.js';
import axios from 'axios';
import {Tabs, Tab} from 'material-ui/Tabs';

class ChooseWallet extends Component {

  constructor(props) {
    super(props);
    this.state = {
      'wallets': null
    }
  } 

  componentDidMount() {
    axios.get("/wallet/list").then((response) => {
      let data = response.data;
      if(data.hasOwnProperty('wallets')) {
        this.setState({
          'wallets': Object.keys(data.wallets)
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
            <WalletList wallets={this.state.wallets} 
                        handleLogin={this.props.handleLogin} 
                        notify={this.props.notify} />
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