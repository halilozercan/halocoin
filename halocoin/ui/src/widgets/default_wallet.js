import React, { Component } from 'react';
import {MCardStats, MCardTable} from '../components/card.js';
import MAlert from '../components/alert.js';

class DefaultWallet extends Component {
  render() {
  	let color = (this.props.wallet === null) ? "danger":"success";
  	let content = (this.props.wallet === null) ? "Not selected!":this.props.wallet.name;
    return (
      <div className="col-lg-6 col-md-12 col-sm-12">
        <div className="card">
          <MAlert type={color} icon="explore" text="Default wallets are stored as decrypted. Any action requiring a wallet will be performed with default wallet if another is not given." />
          <div className="card-content table-responsive">
            Default Wallet: <b>{content}</b>
          </div>
        </div>
      </div>
    );
  }
}

export default DefaultWallet;