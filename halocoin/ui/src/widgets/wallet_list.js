import React, { Component } from 'react';
import {MCardStats, MCardTable} from '../components/card.js';
import $ from "jquery";

class WalletList extends Component {

  render() {
    let content = 'Loading';
    if(this.props.wallets !== null) {
      content = this.props.wallets.map((_row, i) => {
                  return <tr>
                           <td>{_row}</td>
                           <td>Actions</td>
                         </tr>;
                }
              );
    }
    return (
      <div className="card">
        <div className="card-header" data-background-color="yellow">
            <h4 className="title">Wallets</h4>
            <p className="category">List of wallets that are managed by halocoin</p>
        </div>
        <div className="card-content table-responsive">
          <table className="table table-hover">
            <thead className="text-success">
              <tr>
                <th>Wallet Name</th>
                <th align="right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {content}
            </tbody>
          </table>
        </div>
      </div>
    );
  }
}

export default WalletList;