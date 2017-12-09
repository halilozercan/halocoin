import React, { Component } from 'react';
import {MCardStats} from '../components/card.js';
import axios from 'axios';

class Balance extends Component {

  constructor(props) {
    super(props);
    this.state = {
      "address": '',
      "amount": '',
      "password": ''
    }
  }

  onChange = (e) => {
    // Because we named the inputs to match their corresponding values in state, it's
    // super easy to update the state
    const state = this.state
    state[e.target.name] = e.target.value;
    this.setState(state);
  }

  onSubmit = (e) => {
    e.preventDefault();
    let data = new FormData();
    data.append('address', this.state.address);
    data.append('amount', this.state.amount);
    data.append('password', this.state.password);

    axios.post('/send', data)
      .then((response) => {
        if(response.data.success) {
          this.props.notify(response.data.message, 'success');
          this.props.refresh();
          this.setState({
            "address": '',
            "amount": '',
            "password": ''
          })
        }
        else {
          this.props.notify(response.data.error, 'error');
        }
      });
  }

  render() {
    return (
      <div className="col-lg-6 col-md-12 col-sm-12">
        <div className="card card-stats">
        <div className="card-header" data-background-color="Green">
          <i className="material-icons">info_outline</i>
        </div>
        <div className="card-content">
          <p className="category">Balance</p>
          <h3 className="title">{this.props.balance}</h3>
        </div>
        <div className="card-footer container-fluid">
          <form onSubmit={this.onSubmit}>
            <div className="row">
              <div className="col-sm-4">
                  <div className="form-group label-floating is-empty">
                      <label className="control-label">Recipient</label>
                      <input name="address" className="form-control" type="text" value={this.state.address} onChange={this.onChange} />
                  <span className="material-input"></span></div>
              </div>
              <div className="col-sm-4">
                <div className="form-group label-floating is-empty">
                  <label className="control-label">Amount</label>
                  <input name="amount" className="form-control" type="text" value={this.state.amount} onChange={this.onChange} />
                <span className="material-input"></span></div>
              </div>
              <div className="col-sm-4">
                <div className="form-group label-floating is-empty">
                  <label className="control-label">Password</label>
                  <input name="password" className="form-control" type="password" value={this.state.password} onChange={this.onChange} />
                <span className="material-input"></span></div>
              </div>
            </div>
            <button type="submit" className="btn btn-primary pull-right">Submit
              <div className="ripple-container"></div>
            </button>
            <div className="clearfix"></div>
          </form>
        </div>
      </div>
      </div>
    );
  }
}

export default Balance;